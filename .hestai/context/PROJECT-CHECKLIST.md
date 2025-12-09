# Task Tracking

This project uses GitHub Projects for task management.

**Active Board:** https://github.com/orgs/elevanaltd/projects/4

## CLI Access
```bash
gh project view 4 --owner elevanaltd
gh project item-list 4 --owner elevanaltd
```

## Context Note
Task details live in GitHub Projects, not this file. This pointer exists so clock_in returns a valid path while keeping task management centralized.

**Future:** clock_in will become configurable via `.hestai/config.yaml` to define context sources dynamically.
