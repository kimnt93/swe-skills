# Templates: the one style, yours to change

Every issue, plan, pull request body and PR comment follows a template file. **The template is the rule:** the linters
read the sections, their order and what they hold from it, so changing the file changes what every agent must write.

| Text | Template |
|---|---|
| parent issue | [epic.template.md](../assets/epic.template.md) |
| planning card | [planning.template.md](../assets/planning.template.md) |
| build package | [package.template.md](../assets/package.template.md) |
| plan comment | [plan.template.md](../../write-comment/assets/plan.template.md) |
| plan comment on a parent | [epic-plan.template.md](../../write-comment/assets/epic-plan.template.md) |
| **every** pull request body | [pr.template.md](../../work-package/assets/pr.template.md) |
| **every** PR comment: verdict, CTO decision, fix, merge | [pr-comment.template.md](../../write-comment/assets/pr-comment.template.md) |

`package_lint.py templates` prints the file each one is read from.

## What the linter reads

| In the template | The text must |
|---|---|
| a heading | have it, in this order (text after the name, as in `## Verified on <sha>`, is free) |
| `<!-- optional -->` on a heading | may leave it out |
| `<!-- on pass -->`, `<!-- on fail -->` (PR comments) | have it after a PASS or acceptance; after a FAIL or changes required |
| `<!-- on verdict -->` (PR comments) | have it in every `verdict` comment, PASS or FAIL |
| `<!-- needs code -->` | put a command, path or symbol in backticks there |
| `<!-- needs fence -->` | put a fenced block there |
| a `**Label:**` line with a fixed label | have that line (bold or not); with a command in the template line, a command in yours |
| a table header | use the same columns |
| a ``1. **`ID` (title):**`` item | list items in that shape |
| a `- **<name>:**` bullet | write points in that shape |
| a header line such as `Lane:` (issues) | have it |

Sections you add yourself are allowed anywhere.

## What a template does not control

Always checked, whatever the template says: the `Created: <author>` last line, no "Generated with" footer, no secret,
the first line of each comment kind, `Closes #N` on a PR, and the catalog values of an issue.

## Change the style

- **For everyone:** edit the file in this stack, update the filled examples the tests name, run `make docs`,
  `make validate` and `make test`, then reinstall. The GitHub templates for new repositories are copies that
  `make docs` writes.
- **For one project:** put your own `<name>.template.md` (for example `pr.template.md`) in a folder and set
  `AGENT_TEMPLATES=<folder>`. A file there replaces the built-in one; the others stay. Everyone who runs the linter on
  that project, CI included, needs the same setting.
