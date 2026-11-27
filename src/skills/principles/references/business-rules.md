<!-- applies: Apply before a merge or a deploy, and when you rate a change's risk. -->
# Business Rules

The one rule for business rules, for every role and playbook. A business's own policy is not a rule of this plugin: the
project's own agents file (such as `AGENTS.md`) or the operator's instructions state it, such as blocked deploy or merge
windows and which paths are high risk.

- **Read them before a merge or a deploy, and obey them.** Read the file as it is on the base branch, never the pull
  request's own copy: a changed rule binds once it is merged. Where two statements disagree, the stricter holds until
  the person says which.
- **Wait a blocked window out**, unless those rules or the person allow the step. Say what waits and until when, and go
  on with unaffected work. A wait is not a stop and judges nothing. Afterwards read the rules again and run every merge
  or deploy check again. No script checks a window: this is the agent's duty.
- **With none stated, there is no window.** Never invent one, or take one from another project, an example or memory.
- **High-risk paths only add up.** A project's agents file or the operator may add paths and never remove a built-in
  one. An added path is held as a [money path](money-path.md), with all of its rules and its `risk:money-path` label.
  No business rule makes a safeguard, gate or playbook stop weaker.

## What a project writes

A placeholder example for the project's own agents file. Every `<...>` is the project's to fill:

```markdown
## Business rules

- No <merge | production deploy> from <start> to <end> on <days>, <time zone>. May allow an exception: <who>.
- High-risk paths, besides the built-in ones: `<path>`, `<path>`.
```

- **Good:** "The project's agents file blocks production deploys until `<end>`. The change is merged; the deploy waits
  until then. The other two packages go on."
- **Bad:** an agent holds a merge back for a window that no agents file and no operator stated.
