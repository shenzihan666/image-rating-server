# Project Documentation

This directory is the long-form knowledge base for the repository. The root
`CLAUDE.md` only keeps concise project context; detailed guidance lives here.

## Documentation Rules

- Each top-level topic owns a dedicated folder or page.
- Every documentation directory keeps a `README.md` as its local index.
- Topic files use kebab-case English names.
- Change records use `YYYY-MM-DD-topic.md`.
- Runbooks are task-oriented and should list prerequisites, steps, and checks.
- Feature docs should link to related architecture, API, and change documents.

## Recommended Reading Order

1. [Project Overview](./project/project-overview.md)
2. [System Overview](./architecture/system-overview.md)
3. [API Overview](./api/api-overview.md)
4. [Development Docs](./development/README.md)
5. Feature-specific notes under [`features/`](./features/README.md)

## Directory Map

- [`project/`](./project/README.md)
  - Product background, goals, scope, and current focus
- [`architecture/`](./architecture/README.md)
  - System structure, core flows, and module responsibilities
- [`api/`](./api/README.md)
  - HTTP surface, endpoint summaries, and integration notes
- [`development/`](./development/README.md)
  - Commands, environment variables, and engineering conventions
- [`features/`](./features/README.md)
  - Feature-level documentation grouped by domain
- [`changes/`](./changes/README.md)
  - Dated delivery records
- [`runbooks/`](./runbooks/README.md)
  - Operational workflows, checks, and troubleshooting entry points

## Current Focus

The current documentation set emphasizes the Qwen3-VL prompt-management rollout
without losing the baseline project documentation that used to live in
`CLAUDE.md`.
