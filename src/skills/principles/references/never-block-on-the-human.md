<!-- applies: Apply before you ask a question, end a turn to wait for an answer, or record a decision as open. -->
# Never Block on the Human

The one rule for asking, for every role and playbook. It removes needless questions only: no safety rule, merge check,
review gate or playbook stop point gets weaker.

## Go on

- **The request covers the normal steps to finish it.** Don't ask for each one. Your role's limits stay, and a playbook
  still ends where it ends: a plan builds nothing, an audit files nothing. A staging deploy through the project's normal
  pipeline needs no question, within the project's own deploy rules.
- **Look it up first.** Search the code, docs, issues and past decisions for a missing detail. What a command can
  answer, run (the router's prototype playbook).
- **A reversible choice takes the recommended option.** Record it as decided, with its reason, where the work is
  recorded (plan, issue comment, pull request body or report), and continue. It widens no issue, owned-file list or
  accepted plan.
- **Extra work is not a question.** Don't offer it; at most note it in the report.

## Still ask

- real money, trading, accounts or risk limits;
- deleting data, or anything else irreversible, such as a force-push to a shared branch or a message to a customer;
- a production change, or a write on a server (the staging deploy above excepted);
- merging a money-path change;
- publishing publicly, or sending data the issue does not ask for: for data, the issue is updated and accepted first;
- accepting an outsider's issue;
- logins, secrets or access only the owner can give.

A stop that a skill, a playbook, a gate or the project's own rules name stays, listed here or not. Before a merge or a
deploy, the project's [business rules](business-rules.md) hold.

## How to ask

- **One short batch**, each question with your recommendation, answerable from that message alone.
- **Unaffected work continues.** What needs the answer waits.
- **No reply is never approval**, and neither is another agent's yes.
- **Questions go to the CTO/CEO.** Another role sends them along its normal reporting route (an agent: only to the bot
  that started it). The CTO/CEO answers what this rule and the project's rules allow, takes the rest to the owner, and
  never stands in for the owner's approval. A person who gave you the job directly is asked directly.

- **Good:** "Cap set to 50,000 rows (recommended; one setting to change). Waiting only for the production rollout:
  I recommend after the staging check. The other two packages are building."
- **Bad:** "Which cap do you want? Should I also add a progress bar?", and everything stops until a reply.
