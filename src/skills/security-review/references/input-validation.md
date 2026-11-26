# Input validation

## What to look for

Everything from outside: body, query, path, header, cookie, upload, queue message, webhook, file, model output. At the
boundary each needs a **type, a size limit and an allowed set or range**, and what does not fit is refused, not
repaired. Look for missing body and list limits, unknown fields accepted, a client that can set a field it must not
(`role`, `user_id`, `price`), negative or huge numbers, and floats for amounts.

## Bad

```python
data = await request.json()
await orders.create(**data)  # the caller sets any column, "user_id" and "status" included
```

## Good

```python
class NewOrder(msgspec.Struct, forbid_unknown_fields=True):
    symbol: Annotated[str, msgspec.Meta(pattern=r"^[A-Z]{1,12}$")]
    quantity: Annotated[int, msgspec.Meta(gt=0, le=1_000_000)]


async def create(data: NewOrder, request: Request) -> Order:
    return await orders.create(user_id=request.user.id, new=data)
```

## Prove it

A test or local request per case: a missing field, a wrong type, a negative and a huge value, an extra `user_id`, an
oversized body. Expected: 400, 413 or 422, **and nothing written** (read the store back).
