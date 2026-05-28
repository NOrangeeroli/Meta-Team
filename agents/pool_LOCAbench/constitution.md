# LOCA-bench Team Constitution

## Mission
Complete LOCA-bench tasks by interacting with simulated enterprise services through MCP tools, with local_db as fallback.

## Core Principles

1. **Data Completeness**: Process ALL data items — never skip or sample. Evaluation is 100% all-or-nothing.
2. **Precise Output**: Follow output format requirements exactly (column names, email templates, file formats).
3. **Count-First Strategy**: Determine TOTAL items before processing. Verify count matches after.
4. **MCP is unreliable — local_db is the safety net**: MCP servers crash frequently. Every agent must know how to use `workspace/local_db/` as fallback.

## MCP Server Failure Handling (CRITICAL)

MCP crashes are EXPECTED, not exceptional. Every task should be planned with fallback in mind.

**The rule**: If any MCP tool returns `[FATAL MCP ERROR]`, **never call that tool again**. Maximum 2 attempts per tool, then switch to local_db.

**Local_db structure** (Chairman explores in Phase 1 and shares with workers):
- `workspace/local_db/emails/users_data/{email}/emails.json` — email storage
- `workspace/local_db/google_cloud/bigquery_data.db` — SQLite database
- `workspace/local_db/google_sheet/cells.json` — spreadsheet data
- `workspace/local_db/woocommerce/products.json` — product data

**Workers**: Chairman's delegation message includes FALLBACK instructions with exact paths. Follow them.

## Coordination Protocol

- **Chairman** explores workspace + local_db, then delegates with both PRIMARY (MCP) and FALLBACK (local_db) instructions
- **Workers** execute tasks using MCP first, switch to local_db within 2 failed attempts
- **Bulk operations**: Split across workers with non-overlapping ranges
- **Data via files**: Large datasets passed through workspace files, not messages
- **Completion**: Chairman calls `set_final_output` then `terminate`

## Tool Usage

MCP tools via `loca_mcp`:
- `loca_mcp(action="list_tools")` — see available tools
- `loca_mcp(action="call", tool_name="...", arguments='...')` — call a tool

Local_db via `bash`:
- `bash(command="python3 -c '...script...'")` — read/write JSON and SQLite files

## Critical Rules

- **Pagination**: Always iterate ALL pages
- **No assumptions**: Read actual data; never guess values
- **Exact matching**: Evaluation is binary (0/1)
- **Never retry MCP after FATAL error**: Switch to local_db within 2 attempts
