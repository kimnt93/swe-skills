# Authentication and authorization

## What to look for

- **Who:** a new route, socket or job outside the authenticated group; a token read but not verified (signature,
  expiry, issuer, audience, one pinned algorithm); `x-user-id` or `x-username` trusted before the internal token is
  checked ([API contract](../../api-contract/SKILL.md)); a debug or test switch that skips the check; passwords not
  hashed with a slow password hash.
- **May they:** an object fetched by id with no owner or tenant condition; a role checked only in the browser; an admin
  action behind sign-in alone; a default that allows when the rule is missing; removed middleware.

## Bad

```rust
// any signed-in user reads any order by guessing its id
let row = db.query_opt("SELECT * FROM orders WHERE id = $1", &[&id]).await?;
```

## Good

```rust
let query = "
    SELECT id, total
    FROM orders
    WHERE id = $1
      AND account_id = $2
";
let row = db.query_opt(query, &[&id, &caller.account_id]).await?;
```

## Prove it

Tests that **expect refusal**, one per new or changed route: no token and a broken or expired token get 401; user B
asking for user A's object gets 403 or 404 and reads and changes nothing; a plain user on an admin action gets 403.
Take the check away in your checkout: the test must fail. A control no test fails without is not proven.
