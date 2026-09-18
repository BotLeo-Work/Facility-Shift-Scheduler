# Team GitHub Workflow

Use this cycle for every feature or bug fix so `main` stays stable and the
group avoids unnecessary merge conflicts.

```text
main (stable shared code)
  ↓ pull latest
your own branch
  ↓ code + test
commit changes
  ↓ push branch
Pull Request
  ↓ teammate review / resolve conflicts
merge into main
```

## 1. Start with the latest shared code

Before beginning a new task, update your local `main` branch:

```bash
git switch main
git pull origin main
```

## 2. Make a focused branch

Create a branch for one feature or fix:

```bash
git switch -c feature/employee-management
```

Good branch names include:

- `feature/schedule-view`
- `feature/shift-validation`
- `fix/time-overlap`

Do not work directly on `main`.

## 3. Build and test

Make changes only related to the task on your branch. Test the feature before
committing it.

## 4. Review your changes

```bash
git status
git diff
```

Make sure you are not accidentally including unrelated files.

## 5. Commit a clear checkpoint

```bash
git add .
git commit -m "Add employee creation form"
```

Use short, descriptive commit messages that explain what changed.

## 6. Push your branch

```bash
git push -u origin feature/employee-management
```

## 7. Open a Pull Request

On GitHub, create a Pull Request from your branch into `main`. Ask at least
one teammate to look it over before merging. Once it is approved and tests
pass, merge it into `main`.

## 8. Repeat

After a pull request is merged, everyone should update their local `main`
before starting their next task.

## Rules that prevent conflicts

- Announce in your group chat which feature and files you are working on.
- One person should own a file or feature at a time when possible.
- Keep branches small and short-lived; merge completed work promptly.
- Always pull the latest `main` before creating a new branch.
- Do not change another teammate’s branch directly.

## If `main` changes while you are working

Update your branch before opening the Pull Request:

```bash
git fetch origin
git merge origin/main
```

If Git reports a conflict, open the marked file and discuss the intended
version with the teammate who edited the same code. Resolve it, test the
result, then commit the resolution.
