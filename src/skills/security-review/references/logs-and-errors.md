# Sensitive data in logs and errors

## What to look for

Passwords, tokens, cookies, `authorization` headers, keys, seed phrases, card data, personal data, whole request or
response bodies, or a connection string in a log line, a trace attribute, a metric label or an error report; a stack
trace, query, file path or inner host in a response; debug mode on. Formats: [service
logging](../../service-logging/SKILL.md), [service errors](../../service-errors/SKILL.md). A log that leaves the host
is also [outbound data](outbound-data.md).

## Bad

```go
log.Info().Interface("headers", c.GetReqHeaders()).Msg("request") // the token is in there
return c.Status(500).JSON(fiber.Map{"error": err.Error()})        // the query and the host are in there
```

## Good

```go
log.Info().Str("route", c.Route().Path).Str("request_id", id).Msg("request")
log.Error().Err(err).Str("request_id", id).Msg("order read failed")
return c.Status(500).JSON(fiber.Map{"error": "internal error", "request_id": id})
```

## Prove it

Run the request locally with a made-up marker as the token, password and personal field, and force the error. Count
the marker in the captured logs and in the response: both must be 0. `err` itself can carry input: check what it
holds on the failing path.
