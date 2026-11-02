<!-- applies: Apply when sequencing a feature, a refactor or a rewrite. -->
# Subtract Before You Add

First remove what the change makes dead, then build on the smaller base.

- Delete unused functions, dead feature flags, unused env variables (and their `.env.example` lines), unused columns' readers, stale Kafka consumers.
- Remove guards and validators that duplicate one at the boundary.
- Land the deletion as its own commit, green, before the addition. A reviewer then sees two simple diffs instead of one tangled one.
