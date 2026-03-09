# Change Record: Qwen3-VL Prompt Management and UI Update

- Date: 2026-03-09
- Scope: Backend, Frontend, Database, Runtime Configuration, Documentation

## Summary

This delivery establishes a complete Qwen3-VL loop:

- Prompt management in the UI
- Versioned prompt storage
- Runtime prompt injection
- Qwen3-VL result rendering in the image detail page
- Dedicated sidebar navigation for prompt management
- Prompt editor layout refinements with modal-based metadata editing

## Delivered Backend Changes

- Added `ai_prompts` and `ai_prompt_versions`
- Added prompt CRUD and version APIs
- Seeded a default Qwen3-VL prompt at startup
- Updated the Qwen3-VL analyzer to resolve the active prompt at runtime
- Added lightweight prompt template rendering
- Added `.env` fallback support for Qwen3-VL runtime configuration
- Extended `analysis_results` with prompt version metadata

## Delivered Frontend Changes

- Added Qwen3-VL prompt list, create, and detail pages
- Added version history loading and diff comparison
- Added dedicated `Qwen Prompts` sidebar navigation
- Removed prompt buttons from model-specific screens
- Reworked the prompt detail layout
- Moved prompt metadata editing into a modal
- Added structured Qwen3-VL result rendering on the image detail page

## Validation

Validated during implementation:

- `pytest tests/api/v1/test_ai_prompts.py tests/api/v1/test_ai_analyze.py tests/core/test_database_migrations.py -q`
  - Printed `16 passed`
- `npm run type-check`
  - Passed after the navigation cleanup

## Known Issues

- An unrelated existing Next.js build issue remains for `/500` prerendering:
  - `<Html> should not be imported outside of pages/_document`
- The targeted backend pytest command printed a passing summary but the process did
  not exit cleanly before the shell timeout

## Risks and Limitations

- Prompt management currently supports only `qwen3-vl`
- Prompt versions do not have draft or publish states
- There is no rollback action yet
- Structured output is not enforced by a strict schema validator yet

## Recommended Follow-up

1. Add draft and publish states for prompt changes
2. Add prompt rollback support
3. Add a prompt testing workspace
4. Add schema validation for normalized model output
5. Improve CI coverage around prompt lifecycle and process shutdown behavior
