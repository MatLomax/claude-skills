---
description: Initialize worklog for this project (idempotent — creates .solstice/work.db)
---

Run `worklog init` in the project root using the Bash tool.

This creates `.solstice/work.db` for the current project if it does not already
exist. It is idempotent — running it again when the database is already present
is a safe no-op, so never hesitate to run it.

Until this has been run, the worklog MCP tools are inert and report that init is
needed. After it completes, confirm to the user that worklog is ready and that
they can create tasks, record decisions, and link GitHub issues via the worklog
MCP tools.
