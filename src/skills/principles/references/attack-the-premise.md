<!-- applies: Apply when two or more fixes that share one assumption have failed the same check. -->
# Attack the Premise

Stop fixing. Write the shared assumption down and test it directly.

Examples of premises that turn out false: "the consumer sees each message once", "this column is never NULL", "the clock on both hosts agrees", "the test runs against PostgreSQL" (it runs against SQLite), "the env variable is set in staging".

Write a 5-minute probe that checks only the premise (a query, a log grep, a one-off test). If the premise is false, the fixes were aimed at the wrong place: go back to the root cause (the **fix-root-causes** principle).
