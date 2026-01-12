# Phase 0 — Repository Setup & Engineering Standards

## Goals

- Establish a clean monorepo structure
- Enforce modern Python backend engineering standards
- Prepare CI-ready project layout

## Tasks

- Initialize monorepo directory structure:

```bash
services/
libs/
infra/
docs/
```

- Create base service templates with:
- `pyproject.toml`
- `Dockerfile`
- `pytest`, `ruff`, `mypy`
- Implement shared libraries:
- `libs/common`: logging, config, error handling
- `libs/db`: database utilities and migrations
- Configure `pre-commit` hooks

## Deliverables

- Repository skeleton committed
- CI pipeline passing lint and tests

## Acceptance Criteria

- `make test` passes
- Each service can be built as a Docker image
