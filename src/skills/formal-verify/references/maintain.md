# Maintain a formal check

A check that still passes while describing code that no longer exists is the dangerous case.

Outcome per check: **in sync**, **updated** (now describes the code again and passes), **bug** (it
describes the code and the code breaks the property), or **blocked** (say why).

1. **Find the checks:** project skills that run TLC, Hypothesis, rapid, proptest or Kani against named
   code. For each: the property, the covered files, the bounds, the command, the last sync commit.
2. **Run each as it is** and record the result. A pass here only says the old description still holds.
3. **Read every change to covered code** since the sync commit (`git log -p <sync>..HEAD -- <files>`),
   including renames and new code that writes the guarded state. Classify each: no effect / the model
   no longer describes the code / the promise changed on purpose (cite the evidence) / the promise may
   be broken.
4. **Update from the code, not from the result.** Change a property only for a promise that changed
   on purpose; keep the bounds unless the change makes them wrong.
5. **Rerun.** On a pass, break the new code the way the property guards and confirm the check
   catches it. On a failure, replay the counterexample against the real code: if a step can't happen,
   fix the model; if every step can, it is a bug: name the commit that introduced it.
6. **Update the verify skill** and move its sync commit forward (not for a blocked check).

Report per check: the outcome, the commits read, what changed and why, the rerun result, each bug in
plain words.
