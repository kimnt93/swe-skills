<!-- applies: Apply when a diff is growing: a new layer, interface, option, helper or dependency is about to appear. -->
# Laziness Protocol

The best change is the smallest one that solves the problem. Delete before you add.

- One caller → no interface. A Go `interface` with one implementation, a Python `Protocol` or ABC with one subclass, a Rust `trait` with one `impl` is a layer to remove, unless it is a port the application layer owns (a repository, a publisher).
- No new dependency for something the standard library or an already-used library does.
- No option, flag or config value nobody asked for.
- Measure a diff by what a reviewer must hold in their head, not by line count.
