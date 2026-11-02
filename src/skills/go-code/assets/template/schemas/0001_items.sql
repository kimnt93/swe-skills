-- +goose Up
CREATE TABLE items (
    id         uuid PRIMARY KEY,
    name       text        NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
    created_at timestamptz NOT NULL
);
CREATE INDEX items_created_at_idx ON items (created_at DESC);

-- +goose Down
DROP TABLE items;
