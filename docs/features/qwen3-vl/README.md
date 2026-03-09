# Qwen3-VL Feature Overview

## Background

Qwen3-VL had been integrated as a model option, but the surrounding operating model
was incomplete:

- Prompt content lived in code instead of managed storage
- Prompt revisions were not traceable
- The frontend lacked a stable Qwen3-VL result view
- Prompt entry points were mixed into model configuration screens

## Objectives

This delivery adds a usable end-to-end Qwen3-VL workflow:

- Manage prompts in the UI
- Save and compare prompt versions
- Inject the active prompt at runtime
- Render Qwen3-VL responses in the image detail page
- Move prompt access to a dedicated sidebar entry
- Improve the prompt editor layout without changing its functional scope

## In Scope

- Prompt records for `qwen3-vl`
- Prompt version creation, history, load, and diff
- Runtime prompt resolution in the analyzer
- `.env`-backed Qwen3-VL defaults
- Qwen3-VL result rendering in the frontend
- Prompt navigation and layout improvements

## Out of Scope

- Generalized multi-model prompt governance
- Prompt experimentation and evaluation systems
- Prompt sandbox/test-run consoles
- Multi-tenant ownership and permissions
- Advanced template routing or branching logic

## Related Documents

- [Prompt Management](./prompt-management.md)
- [UI Layout Update](./ui-layout-update.md)
- [Change Record](../../changes/2026-03-09-qwen3-vl-prompt-management.md)
