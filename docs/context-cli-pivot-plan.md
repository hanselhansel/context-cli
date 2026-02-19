# Context CLI Pivot Plan (v2.0.0)

## Overview
Pivot from AEO-CLI (Agentic Engine Optimization) to Context CLI (LLM Readiness Linter).
Reframe around token efficiency, RAG readiness, and LLM extraction quality.

## Phase Summary

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Rebrand | DONE | Rename package, purge jargon, hide retail, rename audit->lint |
| 2. Metrics | TODO | Replace 0-100 score with Token Waste % + Pass/Fail checks |
| 3. UX | TODO | Linter-style terminal output (Ruff/ESLint aesthetic) |
| 4. CI/CD | TODO | Updated CI summary + new action.yml inputs for token waste |
| 5. Leaderboard | TODO | New `context-cli leaderboard` command for batch URL comparison |

## Phase 2: Reframe the Metrics

Replace the 0-100 pillar scoring with Token Waste Ratio as hero metric + Pass/Fail checks.

### New Model Fields (ContentReport)
- `raw_html_chars`: Character count of raw HTML
- `clean_markdown_chars`: Character count of extracted markdown
- `estimated_raw_tokens`: Estimated token count (chars/4)
- `estimated_clean_tokens`: Estimated clean token count (chars/4)
- `context_waste_pct`: Percentage of tokens wasted on HTML bloat

### Token Estimation
Simple heuristic: `len(text) // 4`. No tiktoken dependency.

### Pass/Fail Checks
- AI Primitives: llms.txt or llms-full.txt found
- Bot Access: All AI bots allowed in robots.txt
- Data Structuring: At least 1 JSON-LD block present
- Token Efficiency: Context waste < 70% (configurable)

## Phase 3: Linter UX

Target output format:
```
context-cli lint https://docs.anthropic.com

  LINT  https://docs.anthropic.com

  [PASS] AI Primitives      llms.txt found at /llms.txt
  [PASS] Bot Access          13/13 AI bots allowed
  [PASS] Data Structuring    3 JSON-LD blocks
  [WARN] Token Efficiency    85% Context Waste

  -- Token Analysis --
  Raw HTML tokens:     18,402
  Clean MD tokens:      2,760
  Context Waste:       85.0%

  -- Diagnostics --
  WARN-001  Excessive DOM bloat
  INFO-001  Readability grade: 12.3

  1 warning, 0 errors
```

### Color Rules
- Green [PASS]: check passes, waste <30%
- Yellow [WARN]: warning, waste 30-70%
- Red [FAIL]: check fails, waste >70%

### Diagnostic Codes
| Code | Condition | Message |
|------|-----------|---------|
| WARN-001 | waste > 70% | Excessive DOM bloat |
| WARN-002 | no code blocks | No code blocks detected |
| WARN-003 | no headings | No heading structure |
| WARN-004 | bots blocked | AI bots blocked in robots.txt |
| INFO-001 | always | Readability grade |
| INFO-002 | schema found | JSON-LD blocks detected |

## Phase 4: CI/CD Gatekeeper

### New action.yml Inputs
- `max-context-waste`: Maximum acceptable waste % (default: 80)
- `require-llms-txt`: Fail if no llms.txt (default: false)
- `require-bot-access`: Fail if bots blocked (default: false)

## Phase 5: Leaderboard Command

```bash
context-cli leaderboard urls.txt --output leaderboard.md
```

Output: sorted markdown table by Context Waste % ascending.

## Agent Team Protocol
Every phase uses 2-3 agents with git worktree isolation.
Leader creates worktrees, agents commit to own branches, leader merges.
