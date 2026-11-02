//go:build integration

// End-to-end tests against real PostgreSQL, Redis and Kafka (disposable containers):
//
//	docker compose -f docker-compose.infra.local.yaml up -d      # see deployment-setup
//	set -a; . ./.env; set +a; go test -tags integration -race -count=1 ./internal/e2e/...
package e2e

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net"
	"net/url"
	"strconv"
	"sync"
	"testing"
	"time"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
	"github.com/google/uuid"

	"example.com/service/internal/application"
	"example.com/service/internal/config"
	"example.com/service/internal/domain/item"
	"example.com/service/internal/infrastructure/kafkax"
	"example.com/service/internal/infrastructure/postgres"
	"example.com/service/internal/infrastructure/redisx"
	"example.com/service/internal/infrastructure/s3x"
)

var resetOnce sync.Once

// freshDatabase wipes the public schema once per run so reruns and leftovers from other tools never
// leak in. It refuses to touch a database whose name does not look disposable (integration data is
// never production data).
func freshDatabase(t *testing.T, c config.Postgres) {
	t.Helper()
	resetOnce.Do(func() {
		isDisposable := c.Database == "app" || c.Database == "test" || c.Database == "e2e"
		if !isDisposable {
			t.Fatalf("refusing to reset %q: use a disposable database (app, test, e2e)", c.Database)
		}

		dsn := (&url.URL{
			Scheme:   "postgres",
			User:     url.UserPassword(c.User, c.Password),
			Host:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
			Path:     c.Database,
			RawQuery: "sslmode=" + c.SSLMode,
		}).String()

		db, err := sql.Open("pgx", dsn)
		if err != nil {
			t.Fatal(err)
		}
		defer db.Close()

		const resetSQL = `
DROP SCHEMA public CASCADE;
CREATE SCHEMA public
`
		if _, err := db.ExecContext(context.Background(), resetSQL); err != nil {
			t.Fatal(fmt.Errorf("reset database: %w", err))
		}
	})
}

func load(t *testing.T) config.Config {
	t.Helper()
	cfg, err := config.Load()
	if err != nil {
		t.Skipf("integration environment not configured: %v", err)
	}
	return cfg
}

func TestPostgresRoundTrip(t *testing.T) {
	cfg := load(t)
	ctx := context.Background()
	freshDatabase(t, cfg.Postgres)
	if err := postgres.Migrate(ctx, cfg.Postgres, "../../schemas"); err != nil {
		t.Fatal(err)
	}
	store := postgres.Open(cfg.Postgres)
	defer store.Close()
	it, _ := item.New(uuid.NewString(), "pen", time.Now())
	if err := store.Create(ctx, it); err != nil {
		t.Fatal(err)
	}
	got, err := store.Get(ctx, it.ID)
	if err != nil || got.Name != "pen" || got.CreatedAt.Location() != time.UTC {
		t.Fatalf("got %+v err %v", got, err)
	}
	if _, err := store.Get(ctx, uuid.NewString()); !errors.Is(err, application.ErrNotFound) {
		t.Fatalf("missing row must map to ErrNotFound, got %v", err)
	}
	n, err := store.RenameAll(ctx, "pen", "pencil")
	if err != nil || n < 1 {
		t.Fatalf("rename n=%d err=%v", n, err)
	}

	// batch lookup, idempotent upsert, and a SKIP LOCKED claim
	two, _ := item.New(uuid.NewString(), "ruler", time.Now())
	for i := 0; i < 2; i++ { // the second call must converge on the same row
		if err := store.Upsert(ctx, two); err != nil {
			t.Fatal(err)
		}
	}
	list, err := store.ListByIDs(ctx, []string{it.ID, two.ID})
	if err != nil || len(list) != 2 {
		t.Fatalf("list=%v err=%v", list, err)
	}
	claimed, err := store.ClaimOldest(ctx, func(item.Item) error {
		return nil
	})
	if err != nil || !claimed {
		t.Fatalf("claimed=%v err=%v", claimed, err)
	}
	if n, err := store.Count(ctx); err != nil || n < 2 {
		t.Fatalf("count=%d err=%v", n, err)
	}
}

// Zero values are real values: with no pointers, an empty string / false / 0 / the zero time is
// stored as such, never as NULL (the `use_zero` tag), and reads back unchanged.
func TestPostgresZeroValuesAreStoredNotNull(t *testing.T) {
	cfg := load(t)
	ctx := context.Background()
	freshDatabase(t, cfg.Postgres)
	store := postgres.Open(cfg.Postgres)
	defer store.Close()
	if err := postgres.Migrate(ctx, cfg.Postgres, "../../schemas"); err != nil {
		t.Fatal(err)
	}
	id := uuid.NewString()
	if err := store.CreateZero(ctx, id); err != nil {
		t.Fatal(err)
	}
	z, err := store.GetZero(ctx, id)
	if err != nil {
		t.Fatal(err)
	}

	isZeroRow := z.Name == "" && z.Qty == 0 && !z.Active && z.Seen.IsZero() && z.Note == ""
	if !isZeroRow || z.NullsInDB != 0 {
		t.Fatalf("zero row read back as %+v (nulls=%d)", z, z.NullsInDB)
	}
}

func TestS3RoundTrip(t *testing.T) {
	cfg := load(t)
	ctx := context.Background()
	c := s3x.Open(cfg.S3)
	if err := c.EnsureBucket(ctx); err != nil {
		t.Fatal(err)
	}
	if err := c.Ping(ctx); err != nil {
		t.Fatal(err)
	}
	prefix := "e2e/" + uuid.NewString() + "/"
	if err := c.Put(ctx, prefix+"a.json", []byte(`{"a":1}`), "application/json"); err != nil {
		t.Fatal(err)
	}
	got, err := c.Get(ctx, prefix+"a.json")
	if err != nil || string(got) != `{"a":1}` {
		t.Fatalf("got %q err %v", got, err)
	}
	keys, err := c.List(ctx, prefix, 10)
	if err != nil || len(keys) != 1 {
		t.Fatalf("keys=%v err=%v", keys, err)
	}
	if _, err := c.Get(ctx, prefix+"missing"); !s3x.IsNotFound(err) {
		t.Fatalf("a missing key must be ErrNotFound, got %v", err)
	}
	if err := c.Delete(ctx, prefix+"a.json"); err != nil {
		t.Fatal(err)
	}
}

func TestRedisLockIsExclusive(t *testing.T) {
	cfg := load(t)
	ctx := context.Background()
	rc := redisx.Open(cfg.Redis)
	defer rc.Close()
	key := "lock:" + uuid.NewString()
	release, ok, err := rc.Lock(ctx, key, 5*time.Second)
	if err != nil || !ok {
		t.Fatalf("first lock ok=%v err=%v", ok, err)
	}
	if _, ok, _ := rc.Lock(ctx, key, 5*time.Second); ok {
		t.Fatal("a second holder must not get the lock")
	}
	if err := release(ctx); err != nil {
		t.Fatal(err)
	}
	if _, ok, _ := rc.Lock(ctx, key, time.Second); !ok {
		t.Fatal("the lock must be free after release")
	}
}

func TestKafkaPublishConsume(t *testing.T) {
	cfg := load(t)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	topic := "e2e." + uuid.NewString()
	cfg.Kafka.ConsumerGroup = "e2e-" + uuid.NewString()
	prod, err := kafkax.NewProducer(cfg.Kafka)
	if err != nil {
		t.Fatal(err)
	}
	defer prod.Close()

	// Create the topic first: a consumer that subscribes to a missing topic does not notice it
	// until the next metadata refresh (topic.metadata.refresh.interval.ms, 5 minutes by default).
	if err := prod.Publish(ctx, topic, "seed", []byte("seed")); err != nil {
		t.Fatal(err)
	}
	got := make(chan string, 1)

	handle := func(_ context.Context, m *kafka.Message) error {
		got <- string(m.Key) + "=" + string(m.Value)
		cancel()

		return nil
	}

	go func() {
		_ = kafkax.Consume(ctx, cfg.Kafka, []string{topic}, handle)
	}()

	// Publish until the consumer has joined (the consumer starts from "latest", so early messages
	// are skipped).
	for ctx.Err() == nil {
		if err := prod.Publish(ctx, topic, "k", []byte("v")); err != nil && ctx.Err() == nil {
			t.Fatal(err)
		}
		select {
		case v := <-got:
			if v != "k=v" {
				t.Fatalf("got %q", v)
			}
			return
		case <-time.After(2 * time.Second):
		}
	}
	t.Fatal("no message consumed")
}
