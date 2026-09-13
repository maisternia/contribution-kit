# OpenSpec Git Finalization

This repository uses the default OpenSpec flow: create, continue, apply, and
archive changes in the current working tree on the current branch. OpenSpec
skills and `/opsx:*` prompts MUST NOT create, switch, merge, rename, or delete
git branches unless the user explicitly asks for branch management.

## Scope: this repository, plus the superproject gitlink

Every git action described here applies to **this repository**, with one
outward exception: the superproject's gitlink.

`contribution-kit` is consumed as a git submodule (it sits under
`ultralytics-lora/ResearchData/external/contribution-kit` in the Unchirp
superproject). Once a commit here is pushed, updating that gitlink to point at
it is part of finalization. Leaving it behind is what causes drift: the
manuscript cites this repo for figures its own tree still pins to an older
commit.

That bump is the only thing an OpenSpec step may do in an enclosing repository.
Stage the submodule path alone, commit it on its own, and leave every unrelated
edit in that tree uncommitted — the superproject's working tree usually holds
manuscript work that is none of this change's business.

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
archive is a single commit here, followed by the gitlink bump in the
superproject: see
[Scope](#scope-this-repository-plus-the-superproject-gitlink).

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

Then point the superproject at the commit just pushed:

```bash
cd ../../../..   # the Unchirp superproject root
git add ultralytics-lora/ResearchData/external/contribution-kit
git commit -m "Bump contribution-kit to the <name> archive"
git push
```

## Notes

- Keep OpenSpec branch-neutral by default.
- Keep OpenSpec repository-local apart from the gitlink bump: make no other
  change in an enclosing repository.
- Do not merge, rename, or delete branches as part of OpenSpec archive.
- For `bulk-archive`, apply Section 2 to each selected change independently.
- Confirm with the user before any irreversible/destructive git action not
  covered here (e.g. `push --force`, history rewrite, branch deletion).
