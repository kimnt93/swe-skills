### Prototype

**Throwaway code that settles a question by running it.**

1. Write the question as a choice with a measurable answer ("is a Redis stream fast enough at 5k
   msg/s?", "does the Next.js server component render under 200 ms?").
2. Build the smallest sketch that answers it, in a scratch branch or directory, one per alternative
   (2–3). No tests, no polish, no reuse in production.
3. Run each against the same input and record the observation (a number, a screenshot, a log).
4. Present the options with what each gets and costs, and your pick.
5. Delete the sketches; carry the decision (not the code) into [feature](feature.md).

**Reply:** the question, each option's result, the pick and why.
