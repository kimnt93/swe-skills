# Rate limits and resource limits

## What to look for

Sign-in, password reset, codes, sign-up, search, export, anything that sends mail or SMS, calls a paid model or moves
money, and any public endpoint: **is there a limit, and can the caller step around it?** A key from a header the
client sets (a forwarded-for header with no trusted proxy), a counter in each replica's memory, a limit after the
costly work. Also no page-size cap, no timeout, unbounded reads or fan-out per request, a regular expression that
backtracks on crafted input. A removed or raised limit is a change to explain.

## Bad

```python
key = request.headers.get("x-forwarded-for", "")  # a new value per request is a new, empty bucket
if hits[key] > 5: ...                              # and each replica counts its own
```

## Good

```python
key = f"login:{account.casefold()}"  # plus the client address as the trusted proxy reports it
count = await redis.incr(key)        # one counter for every replica
if count == 1:
    await redis.expire(key, 900)
if count > 5:
    raise TooManyRequests(retry_after=900)
```

## Prove it

Against a local instance, send the limit plus one: the last gets **429**. Repeat with a different forwarded-for header
each time: still 429. For size and time limits, send one over: refused before the costly work runs. Never load-test a
shared or live system.
