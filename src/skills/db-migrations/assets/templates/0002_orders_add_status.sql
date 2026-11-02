-- +goose Up
-- Expand: add the column with a default, so existing rows and old code keep working.
ALTER TABLE orders
    ADD COLUMN status text NOT NULL DEFAULT 'open';

-- +goose Down
ALTER TABLE orders
    DROP COLUMN status;
