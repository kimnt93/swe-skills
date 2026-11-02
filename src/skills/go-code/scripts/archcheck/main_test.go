package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, root, rel, body string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func module(t *testing.T) string {
	root := t.TempDir()
	write(t, root, "go.mod", "module example.com/svc\n\ngo 1.22\n")
	return root
}

func TestCleanLayersPass(t *testing.T) {
	root := module(t)
	write(t, root, "internal/domain/order/order.go", "package order\n\nimport \"errors\"\n\nvar ErrX = errors.New(\"x\")\n")
	write(t, root, "internal/application/orders.go", "package application\n\nimport _ \"example.com/svc/internal/domain/order\"\n")
	write(t, root, "internal/infrastructure/postgres/store.go", "package postgres\n\nimport (\n\t_ \"database/sql\"\n\t_ \"example.com/svc/internal/application\"\n)\n")
	write(t, root, "internal/bootstrap/wire.go", "package bootstrap\n\nimport (\n\t_ \"example.com/svc/internal/infrastructure/postgres\"\n\t_ \"example.com/svc/internal/interfaces/httpapi\"\n)\n")
	breaches, err := Check(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(breaches) != 0 {
		t.Fatalf("clean layering must pass, got %v", breaches)
	}
}

func TestBreaches(t *testing.T) {
	root := module(t)
	write(t, root, "internal/domain/order/order.go", "package order\n\nimport _ \"database/sql\"\n")
	write(t, root, "internal/application/orders.go", "package application\n\nimport _ \"example.com/svc/internal/infrastructure/postgres\"\n")
	write(t, root, "internal/interfaces/httpapi/h.go", "package httpapi\n\nimport _ \"example.com/svc/internal/infrastructure/postgres\"\n")
	write(t, root, "internal/domain/order/order_test.go", "package order\n\nimport _ \"net/http\"\n")
	breaches, err := Check(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(breaches) != 3 {
		t.Fatalf("want 3 breaches (domain I/O, application->infrastructure, interfaces->infrastructure; tests skipped), got %d: %v", len(breaches), breaches)
	}
	joined := ""
	for _, b := range breaches {
		joined += b.Reason + "\n"
	}
	for _, want := range []string{"the domain does no I/O", "application may import only domain, application", "interfaces may import only"} {
		if !strings.Contains(joined, want) {
			t.Errorf("missing %q in:\n%s", want, joined)
		}
	}
}
