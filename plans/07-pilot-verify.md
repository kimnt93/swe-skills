# 07 — pilot-verify

status: human (picks the service; makes the CI check required)

## Goal

One real service has hands and eyes: `make verify` runs its static gates **and** a live probe, CI
requires it, and it provably fails on real bugs. Nothing is parallelised on the board before this
holds for the repo the board works on.

## Steps

1. Ask the human for the pilot service (a Go or Python API). Work on a branch in a worktree.
2. In that repo run `/swe:verify-create`. It generates `.agents/skills/verify-<service>/` with a
   feature map of the top 3–5 features, copies `verify.mk`, and vendors the check scripts into
   `tools/skills/`. In the Makefile: `include verify.mk`; set `RUN`, `E2E` and `SERVICE`.
3. `make verify` passes on the clean branch.
4. **Verify the verifier.** On three throwaway branches seed one bug each: a logic bug a test
   should catch; a contract break (`/healthz` body or port); a bad migration (`CREATE INDEX` without
   `CONCURRENTLY` on an existing table). `make verify` must fail on each, for the right reason.
5. Add the `verify` job from the `deployment-setup` workflow template. **Human:** make
   `Validate / verify` a required check on the default branch.
6. For money-path services, add a replay (`/swe:replay-test`): a recorded stream, a replay
   entrypoint, a golden file, and the duplicate and redelivery checks in `make verify`.
7. Open the PR with the `opening-a-pr` playbook.

## Verify

```bash
make verify; echo "exit=$?"                         # 0 on the clean branch, non-zero on each seeded bug
gh api repos/<owner>/<repo>/branches/main/protection --jq '.required_status_checks.contexts'
```

## Log
