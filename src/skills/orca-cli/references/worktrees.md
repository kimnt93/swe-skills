# Orca Worktree Management

Orca structures agent tasks around Git worktrees. Each worktree provides an independent branch and working directory, enabling concurrent multi-agent development without file conflicts.

## Commands

### 1. List Worktrees
```bash
ORCA worktree list --json
```

### 2. Create a Worktree
```bash
ORCA worktree create --repo id:<repoId> --name <branch-name> --json
```
Parameters:
- `--repo`: Target repository identifier or path.
- `--name`: Name for the worktree branch.

### 3. Switch or Focus Worktree
```bash
ORCA worktree focus --worktree <worktreeId> --json
```

### 4. Delete Worktree
```bash
ORCA worktree delete --worktree <worktreeId> --json
```
Cleans up the worktree directory and deregisters it from Orca's session.
