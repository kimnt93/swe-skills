## Architecture & Planning (`<AREA>-00`)

### Code analysis <!-- needs code -->
- `<file or symbol>`: <what exists today, what is reused and what is missing>

### Core design decision (<the model in a few words>)
<the one design for all children, and how each runtime or part uses it>

**Stack:** <languages, libraries, services; each new dependency and why, or no new dependency>
**Rejected:** <the other approach and why it lost>

### Packages & Wave Order

| Wave | Issue | Scope | Key Owned Files | Gate |
|---|---|---|---|---|
| **Wave 1** | `#<n>` (`<AREA>-01`) | <scope> | `<paths>` | `<command>` |
| **Wave 2** *(after #<n>)* | `#<n>` (`<AREA>-02`) | <scope> | `<paths>` | `<command>` |

### Shared-File Sequencing Rules
- **`<file>` (`<AREA>-01` vs `<AREA>-02`):** <who merges first and who rebases>   (or: none, no file is shared)

### Risks & Mitigations
- **<risk>:** <response, and the review every PR needs>

### Decisions <!-- optional -->
1. <the choice>: <the option taken, the recommended one>. Reason: <why>.

### Open Questions <!-- optional -->
1. <only what the asking rule lists under Still ask>. Recommendation: <one>.

Created: <author>
