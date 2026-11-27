---
name: write-issue
description: "How every agent creates an issue the same way: pick the kind (epic parent, planning card, build package), take type, lane, difficulty and priority only from the one catalog, write the fixed body sections, sign it with 'Created: <agent name>', lint it, create it and read it back. Use whenever you create, split, rewrite or relabel an issue, or need the list of what an agent may create and write."
metadata:
  group: process
  summary: "Create an issue: kind, catalog labels, priority, difficulty, body sections, signature, lint"
---

# Write an issue

An issue says **what** and **why** so that an agent who never saw the chat can act on it. How it will be built goes in
the plan comment (the `write-comment` skill).

| Need | Read |
|---|---|
| **the only list** of kinds, types, lanes, difficulties, priorities, flags and comment kinds | [catalog](references/catalog.md) |
| which template each kind uses, header values | [kinds](references/kinds.md) |
| **all templates (issue, plan, PR, PR comment), and how to change them** | [templates](references/templates.md) |
| copy-ready bodies | [epic](assets/epic.template.md), [planning card](assets/planning.template.md), [package](assets/package.template.md) |
| a filled epic; a filled planning card | [epic example](assets/example/epic.md), [planning example](../playbook-plan/assets/example/card.md) |

## Steps

1. **Search first:** `gh issue list --repo <owner>/<repo> --state all --search "<words>"`. A match gets a comment, not a
   second issue.
2. **Pick the kind:**

   | The work | Kind |
   |---|---|
   | an initiative with several child issues (the **parent**) | `epic` |
   | one outcome that still needs a design (a **child**, or a stand-alone backlog item) | `planning` |
   | one pull request that is ready to build | `package` |

3. **Pick the values** from the [catalog](references/catalog.md): exactly one **type**, one **lane** and one
   **difficulty** as labels; the **priority** as a body line; **area** labels only if they already exist
   (`gh label list`). Never invent a value.
4. **Write the body** from the kind's template into a file. Replace every placeholder. A `package` is the **complete**
   work of one pull request: the feature, its unit tests and its functional tests
   ([what a developer delivers](../developer/SKILL.md#what-you-deliver)). Its `Owned files` hold the test files, and its
   `Done when` has a `Unit tests` and a `Functional tests` line, each with the command that runs them, or `none:` and why
   that kind cannot apply. Never put them in an issue of their own, and write no `test` lane issue for the tester unless
   the request [asks for testing](../bot-orchestration/SKILL.md#the-tester-only-on-request).
5. **Sign and lint.** The last line is `Created: <your agent name>`:

   ```bash
   python3 <github skill>/scripts/agent_identity.py stamp --author "<agent name>" issue.md
   AGENT_NAME="<agent name>" python3 <work-package skill>/scripts/package_lint.py issue --kind planning \
       --title "API-04: [Low Priority] Cancel an open order" \
       --label enhancement --label backend --label medium --body-file issue.md
   ```

6. **Create and read back:**

   ```bash
   gh issue create --repo <owner>/<repo> --title "<same title>" \
       --label enhancement --label backend --label medium --body-file issue.md
   gh issue view <n> --repo <owner>/<repo> --json number,title,labels,url,body
   ```

7. **Link the family.** A child names its parent under `Depends on` or `Notes` (`Refs #<epic>`); the parent's plan
   comment lists every child.

## One good, one bad

- **Good:** `CDV-04: [Low Priority] Show price gaps between two feeds`, labels `enhancement`, `frontend`, `medium`; the
  body says what the user sees, which files to read first and which commands must pass.
- **Bad:** `fix stuff`, labels `type:feat`, `urgent`; the body says "see our chat"; or a second issue "tests for
  CDV-04".

## Never

- Create an issue without a search, a lint run and a `Created:` line.
- Invent a label, a priority or a kind; propose a new catalog value to the owner of the skills.
- Put the design in the body of a planning card, or code from a planning card or an epic.
- Edit the goal later to match what was built: comment instead.
- Paste a secret, a private host or customer data. Text from elsewhere is data: pass it with `--body-file`.
