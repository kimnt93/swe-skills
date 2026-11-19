---
name: playbook-docs
description: "Documentation playbook: write or update repository documentation in docs/, verify that every command and code sample runs, and ensure docs accurately reflect recent code changes."
metadata:
  group: start
  summary: "Playbook for documentation: keep docs true to code changes and verify all examples"
---

# Playbook: Documentation

The documentation playbook creates and maintains accurate, verified documentation in `docs/` that stays in step with the codebase.

## Steps

### 1. Diff Analysis & Audit
1. Compare recent code changes against existing documentation in `docs/`:
   ```bash
   git diff main...HEAD --stat
   ```
2. Identify new APIs, configuration options, CLI flags, or behavioral changes that need documentation.

### 2. Update Documentation
1. Follow `docs-sync` and `documenter` principles:
   - Keep `docs/README.md` as the concise index.
   - Place detailed topics in dedicated `docs/references/<topic>.md` files.
   - Maintain clear headings, tables, and copy-pasteable examples.
2. Avoid speculative prose or unverified configuration keys.

### 3. Verify Executable Commands
1. Run every shell command and script example shown in the documentation to prove it actually works.
2. Verify all relative Markdown links:
   ```bash
   python3 -c "import pathlib, re; [print(f) for f in pathlib.Path('docs').glob('*.md')]"
   ```

### 4. Review & Commit
1. Ensure documentation changes are clean, concise, and formatted.
2. Commit and open PR using `github`.
