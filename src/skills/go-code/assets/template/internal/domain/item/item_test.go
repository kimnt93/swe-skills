package item

import (
	"errors"
	"testing"
	"time"
)

func TestNew(t *testing.T) {
	now := time.Date(2026, 1, 2, 3, 4, 5, 0, time.FixedZone("x", 7*3600))
	for _, tc := range []struct {
		name, in string
		wantErr  error
	}{
		{"trims", "  pen ", nil},
		{"empty", "   ", ErrInvalidName},
		{"too long", string(make([]byte, 121)), ErrInvalidName},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := New("1", tc.in, now)
			if !errors.Is(err, tc.wantErr) {
				t.Fatalf("err = %v, want %v", err, tc.wantErr)
			}
			if err == nil && (got.Name != "pen" || got.CreatedAt.Location() != time.UTC) {
				t.Fatalf("got %+v", got)
			}
		})
	}
}
