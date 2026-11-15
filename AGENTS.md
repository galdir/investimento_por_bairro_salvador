## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical triage roles (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` and `docs/adr/` at the repo root). See `docs/agents/domain.md`.

### File editing

Modify existing files in place with targeted `edit_file` patches and reserve `write_file` for new files (`Overwrite=True` only for scratch/artifact files). Consolidate planned edits per file before writing to avoid repeated full-file overwrites and IDE Auto Save conflicts.
