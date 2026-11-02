### Figure it out

**No playbook fits: design one first, then run it.**

1. **Frame:** the done-predicate, the scope in rough units, and the rigour (more for one-way doors
   and money-path, less for reversible low-stakes work).
2. **Design the workflow:** atomic units, riskiest unknown first; the verification harness before the
   work, with a baseline captured from the current state; what can run in parallel (each in its own
   worktree) and what must be sequential. Write the phase list down; that is what the human reviews.
3. **Run the loop:** each unit is an experiment: hypothesis, smallest change, measure on the real
   artefact, keep or revert. A verdict is VERIFIED, NOT VERIFIED or INCONCLUSIVE; inconclusive is
   not a pass.
4. **Keep the trail:** one row per unit in the decision trail; commit it for large work.
5. **Hand back:** check the whole against the predicate on the real system. Turn any repeated
   correction into a check (the **encode-lessons-in-structure** principle). If this playbook will be
   needed again, propose it as a new router playbook.

**Reply:** the playbook you designed, the rigour and why, what is verified, what is open.
