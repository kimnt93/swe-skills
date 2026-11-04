package ormstore

import (
	"os"
	"testing"

	"github.com/glebarez/sqlite"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// ddl is the portable schema the SQLite run creates. A real service owns its schema in goose files
// (go-code/assets/template/schemas, db-migrations); the PostgreSQL run expects those applied.
const ddl = `
CREATE TABLE IF NOT EXISTS items (
    id         text PRIMARY KEY,
    name       text NOT NULL,
    created_at timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS zero_demo (
    id     text PRIMARY KEY,
    name   text      NOT NULL DEFAULT '',
    qty    bigint    NOT NULL DEFAULT 0,
    active boolean   NOT NULL DEFAULT false,
    seen   timestamp NOT NULL DEFAULT '0001-01-01 00:00:00',
    note   text      NOT NULL DEFAULT ''
);
`

// openForTest returns a PostgreSQL store when POSTGRES_HOST is set (the integration run), otherwise
// an in-memory SQLite one, so the same tests prove the adapter on two different databases.
func openForTest(t *testing.T) *Store {
	t.Helper()

	cfg := &gorm.Config{Logger: logger.Default.LogMode(logger.Silent)}

	if host := os.Getenv("POSTGRES_HOST"); host != "" {
		dsn := "host=" + host +
			" port=" + os.Getenv("POSTGRES_PORT") +
			" user=" + os.Getenv("POSTGRES_USER") +
			" password=" + os.Getenv("POSTGRES_PASSWORD") +
			" dbname=" + os.Getenv("POSTGRES_DB") +
			" sslmode=disable TimeZone=UTC"

		db, err := gorm.Open(postgres.Open(dsn), cfg)
		if err != nil {
			t.Fatal(err)
		}

		return New(db)
	}

	db, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), cfg)
	if err != nil {
		t.Fatal(err)
	}

	sqlDB, err := db.DB()
	if err != nil {
		t.Fatal(err)
	}

	sqlDB.SetMaxOpenConns(1)

	if err := db.Exec(ddl).Error; err != nil {
		t.Fatal(err)
	}

	return New(db)
}
