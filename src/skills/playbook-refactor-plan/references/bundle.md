# The bundle

A directory outside every repository: `bundle.json` and one Markdown file per new issue. A complete one is in
[the example](../assets/example/bundle/bundle.json).

```json
{
  "version": 1,
  "bundle": "orders-query-refactor",
  "author": "<the architect's name>",
  "repos": ["<owner>/<api repo>", "<owner>/<web repo>"],
  "parent": "epic",
  "new": [
    {"key": "api-1", "repo": "<owner>/<api repo>", "kind": "package", "title": "ORD-01: <outcome>",
     "labels": ["refactor", "backend", "medium"], "body": "issues/api-1.md"}
  ],
  "old": [
    {"repo": "<owner>/<api repo>", "number": 12, "action": "remove", "reason": "<one line>", "replaced_by": ["api-1"]},
    {"repo": "<owner>/<api repo>", "number": 18, "action": "keep", "reason": "<one line>"}
  ]
}
```

`bundle` is a lowercase name no other plan has used on these repositories. `repos` is every repository in scope: all
their open issues need an `old` entry. No other field exists.

## A new issue

- `kind` `epic` once, for the parent card (the [epic template](../../write-issue/assets/epic.template.md)); every other
  one is a `package` (the [package template](../../write-issue/assets/package.template.md)).
- Title, labels, header lines and sections pass the issue linter, and the labels exist in the repository
  ([catalog](../../write-issue/references/catalog.md)). The last line is `Created: <author>`, the bundle's author.
- A package also has `## Analysis` (what the code does now, naming files in backticks), `## Recommended solution` (the
  approach, shared names and types, and what you rejected), `## Depends on` and `## Owned files`, one `` - `path` `` per
  line.
- **References to new issues** are `{{new:<key>}}`, written without `#`: the script writes `#12`, or
  `<owner>/<repo>#12` in another repository. A plain `#12` means an issue that exists now, and must.
- Every package names its parent as `{{new:<parent key>}}`, and the parent lists every package.
- **Waves** run 1, 2, 3 without a gap. A new issue under `Depends on` is in an earlier wave. Two packages of one
  repository in one wave own no file in common. `Depends on` never names an issue the bundle removes, or one closed
  without being completed.
- No `Pipeline:` line. Do not write the hidden marker line; the script adds it above `Created:`.

## An old issue

`reason` is one plain line of at most 400 characters: it goes into the closing comment. `replaced_by` lists the new
keys that take over its work; leave it out when nothing does, and the reason says why the issue goes. Say `keep` when in
doubt: a kept issue costs nothing, a closed one loses attention.

## The commands

| Command | Reads | Writes |
|---|---|---|
| `check <dir> --offline` | the bundle | nothing |
| `check <dir>` | the bundle and the host | nothing |
| `plan <dir>` | the same | nothing: it prints the dry run and the digest |
| `post <dir> --digest <sha256>` | the same | creates, fills the numbers, closes |

The digest covers `bundle.json` and every body file. `gh` needs write access. A step the script could not finish makes
`post` exit 1 and say which; run it again once the cause is gone.
