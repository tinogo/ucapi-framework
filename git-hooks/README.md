# Git Hooks

This directory contains git hooks for the project. Git is configured to use this directory via:

```bash
git config core.hooksPath git-hooks
```

## Available Hooks

### pre-commit

**File:** `git-hooks/pre-commit`

Runs ruff linting and formatting before each commit.

- Automatically runs `uv run ruff check --fix`
- Automatically runs `uv run ruff format`
- Prevents committing code that doesn't meet quality standards

## Setup

The hooks are already configured! Just install dev dependencies:

```bash
uv sync --group dev
```

The hooks will run automatically via `uv run`, which ensures they use the correct project dependencies.

## Bypassing Hooks

If you need to bypass hooks (not recommended):

```bash
# Skip pre-commit hook
git commit --no-verify

# Skip pre-push hook
git push --no-verify
```
