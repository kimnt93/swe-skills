# Create a formal check

1. **Choose the target from the code:** the promise whose break hurts most and that tests rarely
   reach. In this stack, usually: an order never fills more than its quantity; a fill is applied
   once even when redelivered; a balance never goes negative under concurrent updates; the
   consumer never commits an offset before the database commit.
2. **Pick the tool** from the table in the skill. Prefer what the team can install and run in CI.
3. **Stay true to the code:** every part of the model points to code a reviewer can open
   (`file:function`); what the model treats as one atomic step is one transaction or one locked
   section in the code.
4. **Prove it can fail:** break the guarded code on purpose (drop the dedup check, commit the offset
   first) and show the check catching it. Revert.
5. **Report findings as findings:** a counterexample, told as steps in the code's words, with the harm
   in one sentence. Don't change product code unless asked.
6. **Leave a project-local skill** (`.agents/skills/verify-<property>/SKILL.md`): the property in one
   sentence, the files and functions it covers, the command (`make formal` or a CI job), the bounds,
   and the commit at which the model was last confirmed to match the code. For TLA+, keep a Mermaid
   statechart of the states and transitions next to the model.
7. **Follow the generated skill once** on a scratch change that breaks the property; it must catch it.
