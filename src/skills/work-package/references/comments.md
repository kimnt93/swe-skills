# Comments

A comment is a durable fact on an issue or PR, not a chat message. One comment carries one decision, one plan, one
finding or one status; a reader who was not in the chat must be able to act on it. Use `--body-file` so the text is never
interpolated by a shell.

## Issue comments

### Architect plan

The architect comments on the issue **before** anyone codes. The CTO reads this comment, accepts or asks for one change, and
only then delegates. The plan is not a PR, not a branch and not code.

````markdown
## Plan

Decision: <the one approach chosen; name the alternative and why it lost>

Packages and waves:
| ID | Lane | Difficulty | Owned files | Depends on |
|---|---|---|---|---|
| API-04 | backend | medium | `...` | — |
| UI-09 | frontend | simple | `...` | API-04 |

Contracts:
- <the names, types, routes, schemas or events that must not drift>

Delegation:
- Wave 1: <IDs and the agent/model tier for each>
- Wave 2: <IDs, after what merges>

Verify:
- `<command>` -> <expected output>

Risks / open questions:
- <one line each; "none" when there are none>

Plan SHA: <the design file or commit this reviews, if any>
````

A plan that creates new packages with new IDs also updates the issue body or links the package issues; comments never become
the only place a card exists. An architect who finds the issue unready says so in one comment and stops.

### CTO acceptance

```text
Accepted plan at <date>. Start wave 1: <IDs>. Owner: <bot>.
```

or

```text
Changes required before wave 1:
- <one concrete change>
- <one concrete change>
```

An acceptance is for one plan version. A changed package or file list needs a new acceptance.

### Progress, blocker and close

```text
Status: <started | blocked | done>
Card: <ID>
Evidence: <PR link, commit sha, command output tail>
Next: <the one next action, or none>
```

- A blocker says what is needed and who owns it; "not working" is not a blocker.
- A closed issue says the outcome and the link that proved it. A replacement issue says `Replaces #<n>` in its body and
  links the old issue; the old issue is closed with one comment pointing to the replacement.
- Do not edit the original goal to match the result. Append a comment; edit only the package fields the owner controls.

## PR comments

### Review verdict

The reviewer posts one verdict for one head SHA. A new push needs a new verdict. The body is a file:

````markdown
Verdict: PASS at <full sha>

Reviewed:
- issue and PR body
- diff against main
- `make verify` / the card's exact verify command
- tests and docs

Evidence:
- `<command>` -> `<the tail that proves it>`

Findings: none
````

or

````markdown
Verdict: FAIL at <full sha>

Findings:
1. <title>
   Command: `<command>`
   Got: `<output>`
   Expected: `<what the card requires>`
````

`CHANGES` is not a verdict; use `FAIL`. Opinions without a command and output are dropped. A verdict is never carried to a
new SHA, never copied from another PR, and never posted by the author as approval of their own work.

### Fix response

The author replies on the same PR, not with a new PR:

```text
Fixed in <full sha>:
- <finding title>: <one line of what changed>
- `<re-ran command>` -> <tail>

New head: <full sha>. Please re-review.
```

A reviewer who found a real error does **not** edit the author's branch unless the playbook explicitly names the reviewer as
the fixer; the default is author fixes, reviewer re-reviews. A reviewer who becomes a fixer loses the independent review and
must not post the PASS for that new SHA.

### Merge comment

```text
Merged by the reviewer/gate at <sha> after PASS.
Checks: <required checks and state>.
Post-merge: <issue closed, branch deleted, docs/changelog updated>.
```

The merge is the action, not a promise to merge. It happens only through the project's merge gate, after the verdict at the
same SHA, green required checks and no conflict.

## Never

- Paste a token, password, private host, customer data or an unredacted connection string.
- Put an issue, review or comment body into `bash -c "..."`; write it to a file and pass `--body-file`.
- Use a comment to change scope; update the issue or create a package, then comment.
- Post a verdict for a SHA you did not check, or a `PASS` while a finding is open.
- Write a diary of attempts. State the result, the evidence and the next action.
