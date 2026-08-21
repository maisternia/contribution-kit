# OpenSpec Git Finalization

This repository uses the default OpenSpec flow: create, continue, apply, and
archive changes in the current working tree on the current branch. OpenSpec
skills and `/opsx:*` prompts MUST NOT create, switch, merge, rename, or delete
git branches unless the user explicitly asks for branch management.

## Scope: this repository only

Every git action described here applies to **this repository and no other**.

`contribution-kit` is consumed as a git submodule (it sits under
`ultralytics-lora/ResearchData/external/contribution-kit` in the Unchirp
superproject). That superproject is **out of scope for every OpenSpec step**.
OpenSpec skills and `/opsx:*` prompts MUST NOT `git add`, `git commit`, or
`git push` in any enclosing repository, and MUST NOT update its gitlink to
point at a commit made here — not as archive finalization, not as a courtesy,
not because a workflow step "isn't finished" without it. Publishing a commit
here is the whole of the finalization.

Bumping the superproject's gitlink is a separate, outward-facing act with its
own review surface. It happens only when the user asks for it in that request,
and asking once does not authorize it next time.

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

This repository contains no nested git repositories or submodules, so the
archive is a single commit here. Do not look outward for a second one: see
[Scope](#scope-this-repository-only).

```bash
# Perform the OpenSpec archive move (folder -> openspec/changes/archive/...),
# then commit and push it on the current branch.
git add -A
git commit -m "openspec(<name>): archive change"
git push
```

Before running `git add -A`, check `git status --short` and confirm the working
tree contains only the intended archive/spec-sync work or already-intended
change work. If it also holds unrelated edits, stage the change work by path
instead of using `git add -A`, and leave the rest uncommitted.

## Notes

- Keep OpenSpec branch-neutral by default.
- Keep OpenSpec repository-local: never commit or push outside this repository.
- Do not merge, rename, or delete branches as part of OpenSpec archive.
- For `bulk-archive`, apply Section 2 to each selected change independently.
- Confirm with the user before any irreversible/destructive git action not
  covered here (e.g. `push --force`, history rewrite, branch deletion).
