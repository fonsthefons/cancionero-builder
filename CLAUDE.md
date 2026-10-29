# Working rules for this repo

These rules exist so that every command runs without needing my approval. I often leave tasks running unattended, and a single approval prompt stops all progress until I come back. Follow them strictly.

## Stay inside the repo

- Work only inside this repository. Never read, write, or run anything in folders outside it, except the source repos below.
- Source repos: `/Users/fons/Documents/programs/hymn_books/cancionero`, `/Users/fons/Documents/programs/hymn_books/cancionero-hakuna` and `/Users/fons/Documents/programs/hymn_books/cancionero-pagano`.
  - You may read them freely (Read, Grep, Glob, `ls`, `git log`/`git status`/`git diff` with `-C <absolute path>`).
  - Only write to them, or run code that changes them, when the task explicitly says to. Otherwise treat them as read-only.
  - Their scratch files still go in this repo's `scratch/`.
  - If the Read tool is refused for a file in a source repo, `cat <absolute path>` (one file, no pipes) is allowed instead.
- Book repos: folders `/Users/fons/Documents/programs/hymn_books/<book-name>` created by this builder. Only create or write to them when the task explicitly says to. Tests use folders under this repo's `scratch/`, never `~/Documents`.
- GitHub: never create, delete or change a book repo on GitHub unless the task explicitly says to. Pushing this builder repo to its own GitHub repo is allowed.
- At the start of a session, run `pwd` once to get the repo's absolute path. Use that absolute path in every command.
- Never use `cd`. Always pass absolute paths to commands instead.
- Don't use `/tmp`, `/private/tmp`, or any system temp folder. Put temporary and scratch files in `scratch/` inside this repo (it is gitignored).
- Don't install anything globally. Install packages only into this repo's virtual environment (`.venv/`), if it has one.

## Reading and editing files

- Use the Read tool to look at files, not `cat`, `head`, `tail`, or `sed -n`.
- Use the Edit and Write tools for all file changes. Never modify files with `sed -i`, `awk`, `perl -i`, or shell redirects (`>`, `>>`).
- Use the Grep and Glob tools to search, not shell `grep` or `find`, where possible.

## Running code

- Never use heredocs (`<<EOF`), `python -c`, `node -e`, `bash -c`, `eval`, or `source`.
- Put any code you need to run, even a one-liner, in a file under `scratch/` and run that file.
- If the repo has a virtual environment, run Python as `<repo>/.venv/bin/python` (and `<repo>/.venv/bin/pip`, `<repo>/.venv/bin/python -m pytest`) instead of activating it.

## Shell commands

- Keep commands simple: one command per call.
- No chains with `&&`, `||`, or `;`, no pipes (`|`), no subshells (`$(...)`, backticks), and no variables in paths.
- Use only the absolute paths of real files and folders in this repo or the source repos, written out in full.

## When something is blocked

- If a step seems to require breaking one of these rules or going outside the repo and the source repos (or writing to a source repo without explicit instruction), don't do it. Write it down in `PROGRESS.md` under "Blocked", skip it, and continue with the next step.
- Don't stop to ask me questions while a task is running. Make the most reasonable choice, note it in `PROGRESS.md`, and keep going.

## Progress log

- Keep `PROGRESS.md` up to date: after each phase or major step, add what you did, the main commands you ran, the files you created or changed, and anything that was blocked.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**This project has a knowledge graph. Start with the code-review-graph
MCP tools to narrow scope, then read the source.** The graph is cheaper than scanning files and
gives you structural context (callers, dependents, test coverage) that file search cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes_tool` or `query_graph_tool` instead of Grep
- **Understanding impact**: `get_impact_radius_tool` instead of manually tracing imports
- **Code review**: `detect_changes_tool` + `get_review_context_tool` instead of reading entire files
- **Finding relationships**: `query_graph_tool` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview_tool` + `list_communities_tool`

### Verify in the source

- Narrow scope with the graph, then read the source. Do not change code from graph output alone.
- For any non-trivial change, read the implementation and the relevant tests before concluding.
- Verify the exact source when touching behavior, database logic, migrations, retries, fallbacks,
  recovery, or compatibility code.
- When the graph and the source disagree, the source wins. The graph may be stale or may not
  model that relationship.
- An empty graph result can mean "not indexed" or "not statically visible", not "does not exist".

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes_tool` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context_tool` | Need source snippets for review — token-efficient |
| `get_impact_radius_tool` | Understanding blast radius of a change |
| `get_affected_flows_tool` | Finding which execution paths are impacted |
| `query_graph_tool` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes_tool` | Finding functions/classes by name or keyword |
| `get_architecture_overview_tool` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes_tool` for code review.
3. Use `get_affected_flows_tool` to understand impact.
4. Use `query_graph_tool` pattern="tests_for" to check coverage.
<!-- /code-review-graph MCP tools -->
