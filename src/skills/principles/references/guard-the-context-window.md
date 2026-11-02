<!-- applies: Apply when output is large: long logs, big files, many search results, profiles, fan-out planning. -->
# Guard the Context Window

Keep summaries in the main thread and bulk in subagents or files.

- Send log reading, profile parsing and wide code searches to a subagent; take back the finding, the file:line and the command.
- Brief subagents with paths, not pasted content.
- Save large outputs to a file and quote only the lines that matter.
