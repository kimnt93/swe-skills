<!-- applies: Apply when writing, changing or keeping a test. -->
# Test Behavior, Not Implementation

Assert what a caller can observe, so the test fails when behaviour breaks and keeps passing when only internals change.

- Through the public surface: the HTTP handler (status, envelope, body), the use case's result, the row in PostgreSQL, the message on the topic.
- Against real infrastructure in integration tests (the local compose PostgreSQL, Redis, Kafka), not mocks of your own adapters.
- Table-driven tests in Go, `pytest.mark.parametrize` in Python, a table of cases in Rust.
- A test that only checks that a mock was called with arguments is testing the implementation: replace it or delete it.
