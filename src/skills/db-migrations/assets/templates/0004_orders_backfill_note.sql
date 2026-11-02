-- +goose NO TRANSACTION

-- +goose Up
-- A backfill in bounded batches (no long lock, no huge transaction). Re-runnable: it only
-- touches rows that still need the change.
-- +goose StatementBegin
DO $$
DECLARE
    batch_size CONSTANT integer := 5000;
    updated    integer;
BEGIN
    LOOP
        UPDATE orders
        SET note = 'imported'
        WHERE id IN (
            SELECT id
            FROM orders
            WHERE note = ''
            LIMIT batch_size
        );

        GET DIAGNOSTICS updated = ROW_COUNT;
        EXIT WHEN updated = 0;
        COMMIT;
    END LOOP;
END
$$;
-- +goose StatementEnd

-- +goose Down
-- irreversible: the previous empty notes are not recorded.
SELECT 1;
