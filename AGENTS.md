# Global Baseline for All Projects

These rules apply to every repository unless overridden by a project-level `AGENTS.md`.

## Priorities (highest to lowest)
1. Project-level `AGENTS.md` (cascades and overrides these rules)
2. This global baseline

## Interaction Style
- Respond in **Chinese**.
- Be concise and direct: omit pleasantries, focus on the core answer.
- For lengthy outputs (typically >10 lines of reasoning/code), write to a file instead of dumping content inline.
  - **Directory**: Save to `docs/` under the current project/workspace root. Create `docs/` if it does not exist.
  - **Naming**: Use `docs/<yyyy-mm-dd>-<topic>.md` as the file path (e.g., `docs/2026-08-08-auth-flow.md`).
  - **Output**: Show only the file path and a 1-line summary in the conversation.

## Core Workflow
- Before starting, state a brief execution plan.
- Read a file before editing it.
- Stop and ask if anything is unclear.
- Do not modify unrelated code or perform "drive-by" refactors.
- Do not revert changes unrelated to the current task.
- **When spotting improvement opportunities**: If you notice code worth optimizing but it is outside the strict scope of the current request, do not change it immediately. Instead, leave a `TODO` comment in the original code (e.g., `// TODO: <suggestion>` or the appropriate syntax for the language), and continue with the current task.

## Coding Discipline
- **Match the existing style** of the repository (indentation, naming, language conventions) even if it differs from personal preference. New code must look native.
- Keep changes minimal: make the smallest useful diff, only touch lines necessary for the solution.
- Keep files cohesive; split by feature/responsibility if the project has no established structure.
- Do not introduce new dependencies unless explicitly requested.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tools** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them. `codegraph_node` returns one symbol's source + callers, or reads a whole file with line numbers. If the tools are listed but deferred, load them by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` and `codegraph node <symbol-or-file>` print the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
