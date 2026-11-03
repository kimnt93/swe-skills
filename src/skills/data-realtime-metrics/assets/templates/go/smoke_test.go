package telemetry

import (
	"context"
	"os"
	"testing"
	"time"
)

// TestSmoke emits every metric once so scripts/otlp_check.py can verify the contract:
//
//	python3 scripts/otlp_check.py --role ingestion --wait 20 &
//	OTLP_SMOKE_ENDPOINT=http://127.0.0.1:4318 OTLP_SMOKE_ROLE=ingestion go test -run TestSmoke .
func TestSmoke(t *testing.T) {
	endpoint := os.Getenv("OTLP_SMOKE_ENDPOINT")
	if endpoint == "" {
		t.Skip("set OTLP_SMOKE_ENDPOINT to run")
	}
	ingestion := os.Getenv("OTLP_SMOKE_ROLE") == "ingestion"
	m, err := New(context.Background(), Options{
		Service:     "feed-ws-smoke",
		Environment: "local",
		Endpoint:    endpoint,
		Interval:    time.Second,
		Ingestion:   ingestion,
	})
	if err != nil {
		t.Fatal(err)
	}
	m.SetKafkaHealthy(true)
	m.SetBacklog(func() int { return 3 })
	if ingestion {
		m.SetConnected(true)
		m.SetInFlight(func() int { return 2 })
		m.Reconnect()
	}
	m.Received(true)
	m.Received(true)
	m.Received(false)
	m.Dropped()
	m.Published(128, 4*time.Millisecond)
	m.Error()
	time.Sleep(3 * time.Second)
	// The checker may already have its verdict and closed, so a failed last flush is only logged.
	if err := m.Shutdown(context.Background()); err != nil {
		t.Logf("final flush: %v", err)
	}
}
