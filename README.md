# mat-skills

A private Claude Code plugin marketplace — a single central registry so skills
don't have to be duplicated and fragmented across projects. Registering the
marketplace enables **nothing**; every plugin is `defaultEnabled: false` and is
opted into **per project**.

## Use it

```bash
# once per machine — registers the catalogue, enables nothing
/plugin marketplace add MatLomax/claude-skills

# in a project that wants a skill — writes .claude/settings.json (committed)
/plugin install image-to-html@claude-skills --scope project
#   …or --scope local to keep it out of git
```

Update later with `/plugin marketplace update claude-skills`.

## Plugins

| Plugin | What it does |
|---|---|
| `image-to-html` | Reconstruct HTML from a mockup image and objectively gate the render against it — per-region SSIM, edge-XOR border detection, colour/tint sweeps, glyph measurement. Explicit-invoke only. |
| `worklog` | Per-project, SQLite-backed task & decision log for coding agents, remembered across sessions — task tree with blocking, GitHub-issue links, first-class decisions, and a per-session journal, over MCP. Run `/worklog:init` per project. **Requires the [`worklog`](https://github.com/MatLomax/worklog) binary on PATH.** |

## Layout

```
.claude-plugin/marketplace.json      # the catalogue
plugins/<name>/
├── .claude-plugin/plugin.json       # plugin manifest
└── one or more of:
    ├── skills/<name>/SKILL.md        # a skill + its scripts/ and assets/
    ├── .mcp.json                     # an MCP server
    ├── hooks/hooks.json              # SessionStart/Stop/… hooks
    └── commands/<name>.md            # a /plugin:command
```

Add a new plugin by dropping another `plugins/<name>/` and listing it in
`marketplace.json`. `worklog` is the MCP+hooks+command shape; `image-to-html`
is the skill shape.
