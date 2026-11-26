# Security audit: orders service at 7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d

## Scope
Every file at that head of `main`. The code is the team's own, so its tests and a local instance ran, with a
disposable database and made-up data. Nothing deployed was touched.

## Findings

### F1, high: any signed-in user reads any order
- **Where:** `api/orders.py:31` selects by id with no account condition.
- **Proof:** `pytest -q /home/example/audit-evidence/orders/test_other_user.py`

```text
>       assert response.status_code == 404
E       assert 200 == 404
1 failed
```

- **Gets:** user B reads the lines and total of user A's order by its id.
- **Smallest fix:** add the caller's account to the query, with that test.

### F2, medium: the nightly job sends customer emails to a service no issue names
- **Where:** `jobs/stats.py:12` posts each whole order object to `stats.vendor.test`.
- **Proof:** `python3 /home/example/audit-evidence/orders/capture_stats.py` (the job against a local fake receiver)

```text
POST /v1/orders fields: email, id, status, total
```

- **Gets:** a third party holds customer emails. The only issue found asks for order counts.
- **Smallest fix:** stop the call, or the owner accepts an issue that names the destination and the data.

## Outbound paths

| Destination | Data | Code | Asked by |
|---|---|---|---|
| `payments.vendor.test` | order id, amount, currency | `api/pay.py:22` | #14 |
| `stats.vendor.test` | whole order, email included | `jobs/stats.py:12` | no issue found (F2) |
| the service's own PostgreSQL | orders | `db/orders.py` | its own datastore |
| the project's package registry, in CI | none beyond the install | `.github/workflows/ci.yml:18` | #3 |

## Scan items
`security_scan.py --tree 7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d`: exit 1, 6 items. 2 are F1 and F2; 3 are the other
outbound paths above; 1 is a made-up password in `tests/conftest.py`, used by the disposable database only.

## Not checked
- The payment webhook's signature check: it needs the provider's test key.
- CI and containers: reading only, no image was built.
- Wallet and chain code: the service has none.

## Issues ready to file (not filed)
1. [Only the order's owner reads it](issue-order-owner.md), for F1.
2. For F2 the owner first decides whether the data should leave at all.

Created: Reviewer (example) / auditor
