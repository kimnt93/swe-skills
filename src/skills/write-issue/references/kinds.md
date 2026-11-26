# The body of each kind

**The template is the format.** Its sections, their order and its guidance are the rule, and the linter reads them from
the file ([templates](templates.md): how to read and change them). Copy it, replace every `<...>`, drop an optional
section you have nothing for.

| Kind | Template |
|---|---|
| `epic` (the parent) | [epic.template.md](../assets/epic.template.md) |
| `planning` (a child, or a backlog item) | [planning.template.md](../assets/planning.template.md) |
| `package` (ready to build) | [package.template.md](../assets/package.template.md) |

## Header lines

| Line | Value |
|---|---|
| `Lane:` | equals the lane label |
| `Wave:` | epic: `0 (Epic)`; planning: a number or `Backlog (priority and what it waits for)`; package: a number |
| `Difficulty:` | equals the difficulty label; one sentence on why may follow |
| `Priority:` | `low`, `medium`, `high` or `urgent` |

## What makes it good

- **Standalone:** names every file and command; nothing depends on a chat.
- **Runnable proof:** each `Done when` is a command; "works" is not.
- **Right size:** a package is one PR of a few hundred changed lines. Two packages of a wave never own the same file.

## Signature

The last line, always, is `Created: <author>`: the agent's own name as its instructions give it, never the account's or
the human's. No "Generated with" or other tool footer.

## Replacing an old issue

If it cannot be solved as written: create a new issue that says `Replaces #<n>`, and close the old one with a `close`
comment pointing to it.
