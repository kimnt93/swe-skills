<!-- applies: Apply to multi-step work (migrations, sweeps, many similar edits) and to how commits and PRs are ordered. -->
# Sequence Verifiable Units

Break the work into small units that each end green, check each before starting the next, and order them so the sequence explains itself.

- One commit per unit; `make verify` (or the unit's check) passes at every commit.
- Order: deletions, then scaffold (types, ports, migrations), then behaviour, then cleanup.
- For migrations: expand, migrate, contract, each its own PR.
- Never batch "I'll test it all at the end": a failure then has ten suspects.
