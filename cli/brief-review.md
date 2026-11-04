Start with the {plugin} skill ({start}).

You are reviewing card {card} of project {project}, not fixing it. Do not edit, commit or push.
Use the interrogate skill on: git diff {base_ref}...HEAD
The change is meant to do this: {goal}
Keep only findings you proved by running a command in this worktree. For each: title, the exact
command, the output it printed, the output the card requires. Write the report to .swe/review.md.
If nothing is proven, write: no verified findings.
Your last line is exactly one of:
  REVIEW DONE <head sha> <n> verified finding(s)
  REVIEW BLOCKED <one-line reason>
