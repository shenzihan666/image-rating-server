# Qwen3-VL Prompt UI Layout Update

## Overview

This update changes layout and navigation only. Existing prompt management behavior
is preserved.

The design goals were:

- Make the editor the dominant workspace
- Keep version history visible at all times
- Move low-frequency metadata edits out of the main canvas
- Use a stable sidebar entry instead of action buttons embedded in model screens

## Navigation Update

### Before

Prompt access was exposed through model-related screens, which mixed runtime
configuration with prompt content management.

### After

Prompt management now has a dedicated sidebar entry:

- `Qwen Prompts`

The prompt buttons were removed from:

- The AI model overview page
- The single-model configuration page

Benefits:

- Stable entry point
- Clearer separation between runtime configuration and prompt authoring
- Less noise in model management screens

## Prompt Detail Layout Update

### Layout Principles

- The main content area is reserved for prompt editing
- Version history sits on the far-right as a vertical rail
- Metadata editing moves into a modal
- Existing save, load, and compare flows remain unchanged

### Top Actions

The top action bar now exposes:

- `Metadata`
- `Compare Versions`
- `Save New Version`

`Metadata` sits immediately to the left of `Compare Versions`.

### Editor Area

`System Prompt` and `User Prompt` editors were expanded to take most of the page.
This improves long-form editing and makes the relationship between both prompts
easier to inspect.

### Version History Rail

Version history is displayed as a dedicated right-side vertical column so users can:

- See history without leaving the editor
- Load an older version quickly
- Preserve the width of the main editing surface

### Metadata Modal

Prompt metadata is now edited in a floating modal rather than a persistent card.

Editable fields:

- Name
- Description
- Active-state toggle

This keeps the primary workspace focused on prompt content while still exposing the
same metadata controls.

## Functional Stability

The following behaviors were not changed:

- Prompt list loading
- Version history loading
- Loading a version into the editor
- Saving metadata
- Saving a new version
- Version diff
- Active prompt switching

## Follow-up Suggestions

1. Add history search and filtering
2. Surface draft-versus-loaded-version status in the editor
3. Add keyboard shortcuts for modal save actions
4. Add inline syntax highlighting improvements in diff mode
