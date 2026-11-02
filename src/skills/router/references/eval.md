### Eval

**Change a skill, a prompt or a model choice only with a blind comparison.**

1. Fix the cases: 5–10 real past tasks (a bug, a feature, a review, a card split) with what a good
   result looks like, written before you run anything.
2. Prepare each candidate (old vs new skill text, or model A vs model B) in its own clean directory.
   Strip words that reveal it is a test (`eval`, `judge`, `benchmark`) from what the candidate sees.
3. Run every case on every candidate with the same prompt.
4. Judge blind: a judge on another model family sees outputs under neutral labels and the rubric,
   never the candidate names. Score each case.
5. Check the transcripts, not the self-reports: did the candidate actually run the commands it claims?
6. Keep the change only if it is not worse on any case that matters and better on some.

**Reply:** the cases, the scores per candidate, the decision.
