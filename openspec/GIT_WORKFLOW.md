# OpenSpec Git Finalization

This repository uses the default OpenSpec flow: create, continue, apply, and
archive changes in the current working tree on the current branch. OpenSpec
skills and `/opsx:*` prompts MUST NOT create, switch, merge, rename, or delete
git branches unless the user explicitly asks for branch management.

## Definitions

- **`<name>`** = the kebab-case OpenSpec change name (the "feature-name").

## 1. When a change STARTS

No git branch action is required. Run the normal OpenSpec command and continue
on the current branch:

```bash
openspec new change "<name>"
```

## 2. When a change is ARCHIVED

After any requested spec sync and the OpenSpec archive move (`mv
openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>`), commit
and push the archive result on the current branch:

If the change includes edits inside nested git repositories or submodules,
commit and push those repositories first. The parent repo archive commit should
capture the updated gitlink or vendored snapshot only after the nested repo work
has its own published commit.

```bash
# Perform the OpenSpec archive move (folder -> openspec/changes/archive/...),
# then commit and push it on the current branch.
git add -A
git commit -m "openspec(<name>): archive change"
git push
```

Before running `git add -A`, check `git status --short` and confirm the working
tree contains only the intended archive/spec-sync work or already-intended
change work.

## Notes

- Keep OpenSpec branch-neutral by default.
- Do not merge, rename, or delete branches as part of OpenSpec archive.
- For `bulk-archive`, apply Section 2 to each selected change independently.
- Confirm with the user before any irreversible/destructive git action not
  covered here (e.g. `push --force`, history rewrite, branch deletion).
