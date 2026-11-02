# Feature map shape

`features/README.md` indexes the features; each feature file answers, from the user's side: what it
is, how to reach it, how to drive it, and what proves it worked.

## Example: an API feature (`features/place-order.md`)

```markdown
# Place an order

A client places a limit order and gets its id; the order appears in the order book and on the
`orders.placed.v1` topic.

## Sub-features
- `place-limit`: a valid limit order is accepted (201).
- `place-reject`: an order over the risk limit is rejected (422, `error.code = risk_limit`).

## How to get to it (caller's view)
`POST /v1/orders` with the internal service token.

## Driving it
curl -sS -X POST http://127.0.0.1:3000/v1/orders \
  -H "x-internal-service-token: $INTERNAL_SERVICE_TOKEN" -H 'content-type: application/json' \
  -d '{"symbol":"VN30F","side":"buy","qty":1,"price":"1250.5"}'
Then: `GET /v1/orders/<id>`; read one message from `orders.placed.v1`; `SELECT status FROM orders WHERE id = ...`.

## Proof
201 with `success: true` and an id; the GET shows `status: open`; one message on the topic; one row.

## Gotchas
The risk service must be up (its `/healthz`), or every order is rejected.
```

## Example: a frontend feature (`features/orders-page.md`)

```markdown
# Orders page

A trader sees today's orders, filters by symbol, and cancels an open order.

## How to get to it
Open `/orders` after signing in.

## Driving it (Playwright)
await page.goto("/orders");
await page.getByRole("combobox", { name: "Symbol" }).selectOption("VN30F");
await page.getByRole("row", { name: /open/ }).getByRole("button", { name: "Cancel" }).click();

## Proof
The row's status changes to `cancelled`; the API received `DELETE /v1/orders/<id>`; a screenshot.

## Gotchas
Seed data: at least one open order for VN30F (the e2e seed script creates it).
```
