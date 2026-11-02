<!-- applies: Apply when code is hard to follow: many layers between a question and its answer, or hidden state. -->
# Minimize Reader Load

Count the hops a reader makes to answer one question, and cut them.

- Collapse one-caller wrappers and pass-through layers.
- Keep mutable state small and local: no package-level variables (Go), no module globals (Python), no `static mut` (Rust).
- Prefer a function that fits one screen and reads top to bottom, per the language skill's `readable-code` reference.
- A refactor that does not lower reader load somewhere is not worth keeping.
