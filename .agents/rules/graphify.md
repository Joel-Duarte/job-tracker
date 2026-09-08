---
trigger: always_on
description: Fast codebase navigation using Graphify (architecture/macro) and Ripwire (symbols/micro/verification).
---

## Codebase Navigation: Graphify (Macro) + Ripwire (Micro)

This project has both **Graphify** (`graphify-out/graph.json`) and **Ripwire** installed.

### 1. Macro / Architecture Questions (Graphify)
For system-level understanding, cross-module relationships, or high-level architecture:
- When `graphify-out/graph.json` exists, run `graphify query "<question>"` (CLI) first.
- Use `graphify path "<A>" "<B>"` for component relationships and `graphify explain "<concept>"` for focused concepts.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost).

### 2. Micro / Tactical Code Search & Verification (Ripwire)
For finding exact symbols, checking callers, and verifying changes without reading entire files:
- **Locate symbols/implementations:** `ripwire . --for="<task or symbol>"` (returns exact definitions, signatures, complexity, and line numbers in ~2K tokens).
- **Find callers & usages:** `ripwire . --callers="<symbol>"` (1-hop call hierarchy) or `ripwire . --uses="<symbol>"`.
- **Check impact & blast radius:** `ripwire . --impact="<symbol>"` before modifying shared code.
- **Post-edit verification:** `ripwire . --situ` (checks uncommitted edits for transitive blast radius, affected stores/files, and exact tests to run).

### 3. Tool Precedence (Strict Policy)
- **Do NOT use native `grep_search` or `find_by_name` as default code exploration tools.** They produce noisy unranked hits and force reading entire files.
- **Prefer `run_command` with `ripwire` or `graphify`** for all code search, symbol lookup, and architecture questions.
- Reserve `grep_search` strictly for exact literal string matches (e.g. raw UUIDs, error message strings, or regexes).
