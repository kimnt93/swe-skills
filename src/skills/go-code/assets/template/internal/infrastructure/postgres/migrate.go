package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"net"
	"net/url"
	"strconv"

	// database/sql driver for goose only; the service itself uses go-pg.
	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"

	"example.com/service/internal/config"
)

// Migrate applies the immutable goose files in dir ("schemas"). Run it as a one-shot job (`api
// migrate`) before the service rolls out; never edit a released file, add a new version.
func Migrate(ctx context.Context, c config.Postgres, dir string) error {
	db, err := sql.Open("pgx", dsn(c))
	if err != nil {
		return fmt.Errorf("open for migrate: %w", err)
	}
	defer func() {
		_ = db.Close()
	}()

	if err := goose.SetDialect("postgres"); err != nil {
		return err
	}

	return goose.UpContext(ctx, db, dir)
}

// dsn builds the connection URL for the migration driver. It contains the password: never log it.
func dsn(c config.Postgres) string {
	u := url.URL{
		Scheme:   "postgres",
		User:     url.UserPassword(c.User, c.Password),
		Host:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
		Path:     c.Database,
		RawQuery: "sslmode=" + c.SSLMode,
	}

	return u.String()
}
