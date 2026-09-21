# Codex handoff 005 — Assess a bounded code-and-documentation release candidate

Status: saved for a future session; not executed. Do not continue the unfinished broad preparation handoff 004.

## Pre-dispatch assessment

- Deliverable: one exact proposed public file list and short readiness decision in docs/Code-docs release candidate.md. This is a review milestone, not publication or a declaration that the whole repository is cleared.
- Effort: moderate, with uncertainty from code ownership, source-derived examples and legacy history. No reliable token or duration estimate is available. Limit the work to the candidate paths and known blockers; do not attempt exhaustive legal or history review.
- Expensive work: zero database builds, exports, renders, bulk downloads, environment creation or full test-suite runs.
- Verification: bounded file inventory, candidate-content review, existing validation-report inspection and a check of proposed relative links. Do not rerun scientific validation.
- Checkpoints: missing license choice, ambiguous ownership/redistribution, unexpected large scope or any need to rewrite history, change implementation or run expensive checks. Complete independent in-scope inventory first, then return unresolved items together.
- Stop: deliver the candidate list and disposition of each known blocker. Do not commit, stage a broad file set, create a remote, export a publication tree, push or publish.

## Context and accepted constraints

Workspace: C:/Users/aweyr/OneDrive/Documents/Cheng-Lab/Tool-Development/ligand-receptor-database.

Read current AGENTS.md, README.md and docs/Repository readiness.md. Inspect Git status and preserve unrelated changes. The last broad preparation run was stopped for excessive resource consumption; unfinished verification is not permission to resume rebuilding. AGENTS.md is local-only and ignored; its removal from the Git index does not erase its history.

Known blockers reported by the prior task:

1. No selected code license; the historical LICENSE was empty.
2. Data terms are unresolved: ConnectomeDB's conflicting terms, heterogeneous OmniPath restrictions, GtoPdb obligations and derived-output redistribution.
3. Existing Git history includes historical data and potentially personal paths.
4. Rebuilding requires separately supplied, pinned annotation assets.
5. Final preparation checks were not confirmed complete when work stopped.

Scientific data must remain local and unchanged. Do not include source/intermediate/processed/historical datasets, manifests exposing personal paths, derived examples, user-specific instructions, Obsidian state, credentials or handoff notes in the proposed first public candidate. Do not delete them to achieve this. Documentation must not imply unverified standalone reproducibility or automatic access to the two blocked providers.

## Bounded review

1. Inventory the current project-owned code, dependency files, synthetic tests and generic documentation proposed for publication. Produce an explicit allowlist with purpose and any condition per path. Existing dictionary/examples and source mappings are not automatically generic documentation: review whether they contain source-derived material, and mark uncertain files withheld. Check fixture provenance rather than assume all tests are synthetic.
2. Read the current README and proposed setup instructions for personal paths, unsupported commands, missing annotation prerequisites and references to withheld files. Record small precise edits needed for a later candidate-preparation task; do not redesign dependencies or reconstruct the annotation resource now.
3. Check candidate text for credential-like material and personal paths without printing secret values. A bounded scan is not proof that no sensitive content exists. Do not inspect unrelated personal directories.
4. Review the existing readiness/audit records concerning Git history. At most inspect the tracked-path inventory and a bounded recent history summary to establish whether the existing history is unsuitable for this candidate. Do not scan every historical blob or rewrite history. Recommend a new clean, explicitly allowlisted publication tree if the existing history cannot be cleared cheaply; state that copying/exporting it requires a separate accepted task. A .gitignore entry does not remove tracked files or history.
5. If the user has not selected a code license, explain that this is still their choice and request it in the final checkpoint. Do not silently default to MIT or infer ownership from the project location. Identify institutional/coauthor ownership uncertainty if evident. Do not launch a legal research project; use official sources only if a specific license fact is needed.
6. Report prior validation accurately: distinguish completed checks from pending checks and note whether implementation hashes changed afterward. Do not claim old test results validate current bytes. Propose only the minimum candidate-level verification for a subsequent session. Missing full scientific rebuild verification need not be disguised or repaired during this review.

## Output and stopping boundary

Write docs/Code-docs release candidate.md with:

- Exact proposed included paths, withheld categories and reasons.
- Minimal README/setup edits needed and external annotation prerequisites.
- Code-license/ownership decision still required, if any.
- Recommended existing-history versus clean-tree publication approach, without executing it.
- What was checked, what remains unverified and known access/data restrictions.
- One small next handoff proposal with an effort estimate, explicit checks and zero automatic scientific rebuilds.

Return a concise accession-labeled summary and any required user decisions. Do not fix every discovered issue, resume handoff 004, conduct full redistribution clearance or proceed automatically to the proposed next task. If the review itself exceeds its bounded scope, preserve the partial report and return a checkpoint.
