# Examples

| Directory | Mode | What |
|---|---|---|
| [pm-jlogger/](pm-jlogger/README.md) | pm | a project manager runs plan, build, review, merge workflows around the upstream `jlogger` |
| [dev-gorouter/](dev-gorouter/README.md) | dev | a developer's agent takes an issue to an open PR (no review, no merge) around the upstream `gorouter` |

Both keep their upstream repo as a git submodule: `git clone --recurse-submodules`, or `git submodule update --init`.
Each has a `setup.sh` that rebuilds it from nothing with `swe-cli`.
