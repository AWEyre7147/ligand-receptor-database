# Codex handoff 004 — Document, comment and prepare the repository for GitHub

Status: ready for implementation; not executed. This is the closing documentation and repository-preparation milestone, not authorization to push or publish.

## Objective

Create a comprehensive field guide, document every project script, apply the user's established commenting conventions, remove demonstrably unnecessary artifacts, and prepare a clean, understandable repository for GitHub. Preserve scientific behavior, source data, accepted policies and output traceability. Complete the work, rather than returning only cleanup recommendations.

Project root: `C:/Users/aweyr/OneDrive/Documents/Cheng-Lab/Tool-Development/ligand-receptor-database`.

Read applicable instructions, Git status, accepted policies, existing docs/Database dictionary.md, docs/Final database build.md, source acquisition/normalization docs and all current manifests. Inspect actual schemas and code. Do not treat prose or generated reports as a substitute for verifying implementation. Existing working-tree deletions predate this milestone; do not reset or restore the old project wholesale.

## 1. Field guide

Expand or replace docs/Database dictionary.md as the authoritative field guide rather than create a competing dictionary. Make it approachable for a biomedical researcher unfamiliar with complexes, proxy ligands and database engineering. Introduce what a row means in each table and how to follow an interaction to its original evidence.

Cover every column in every final Excel sheet and Parquet table: primary human/mouse interactions, nonprotein/proxy companions, assertions, review, entities, evidence, complex definitions/members, original source members, regulators, sources, Readme and all Shared-* tables. Cover normalized intermediate schemas in a separate clearly labeled section or linked note. Document manifest fields separately as operational metadata. If human and mouse schemas are identical, document them once and explicitly state applicability; do not duplicate identical definitions.

For each field document:

- Exact field name, table(s), data type, and Excel versus Parquet representation.
- Plain-language definition, entity/record level and scientific interpretation.
- Content format, namespace, allowed values or reference vocabulary, units where applicable and a verified representative example.
- Missing-value meaning, including unknown versus not applicable versus false/zero; do not invent distinctions the implementation does not retain.
- Origin: exact upstream source field(s) and transformations, or an explicit pipeline-derived designation. Link to the relevant script/function and source documentation. For heterogeneous aggregated fields provide a source-to-field mapping, not a vague statement that it comes from databases.
- Keys, foreign-key relationships, cardinality and joining instructions, with interpretation caveats.

Document status/reason/provenance vocabularies, ID generation and stability limits, raw JSON payloads, list serialization, membership roles, stoichiometry, encoded_by relations and regulator distinctions. Explain that an interaction is not necessarily a single gene pair, a proxy is not its product, inferred mouse evidence is not native experimental proof, and source/publication counts are not independent-replication scores. Explain the actual companions currently contain proxies rather than imply molecule-only coverage that the build has not achieved.

Include a few verified worked examples spanning a simple pair, a complete complex, inferred mouse provenance, a proxy and a review record. Follow actual IDs through supporting tables; do not invent rows. Small diagrams/tables are optional only where useful. Include a short safe-loading/join example and clarify which tables most users need first.

Validate dictionary coverage automatically against actual final and intermediate schemas, including empty tables, and check documented enumerations against code/data. Prefer one maintained schema description where feasible; avoid rewriting runtime code just to generate documentation.

## 2. Script documentation and root entry point

Create docs/Script guide.md covering every maintained project-owned Python/JS/R script and helper discovered during inventory, not dependencies or disposable scratch code. Current Python modules include download_sources, source_registry, normalization_core, source_normalizers, normalize_sources, normalization_report, validate_normalization, database_identity, database_build, database_export and build_databases. Inventory any additional build/render/validation helpers and tests before deciding what is necessary.

For each script/module describe purpose, entry point versus imported helper, CLI flags with defaults, inputs/outputs, dependencies, execution order, scientific responsibilities, side effects, failure/exit behavior, locks/recovery, and tests. Give commands verified against the implementation. Explain which operations access the network and which are offline. Document manual imports, LRdb TLS and GtoPdb authentication limitations honestly. Never recommend disabling TLS verification or committing credentials.

Create a current root README.md with the project purpose, human/mouse scope, output links, simple installation/use commands, workflow diagram or short sequence, documentation navigation, limitations and citations/data-term guidance. Clearly separate downloading sources, normalization and final building. Do not silently introduce a new all-in-one workflow command in this documentation milestone.

Audit portability: the current environment used bundled Python packages through system site packages and build previews use a Codex-provided Node artifact runtime. Identify and document hidden dependencies, personal absolute paths and the sibling annotation-resource dependency used for identity mapping. Verify setup from declared dependencies in an isolated temporary environment where practical, without relying on the existing .venv. Make small necessary configuration fixes if required for documented commands, with focused tests. Do not claim a standalone GitHub clone can reproduce outputs until verified or explicitly document any remaining prerequisites. Do not copy the entire sibling annotation project; pin/checksum the required reference assets and provide a supported location/configuration method. Keep substantive dependency/toolchain redesign out of scope and report any genuine blocker.

Use Markdown that works both in Obsidian and on GitHub. Preserve docs/.obsidian locally; avoid publishing user-specific workspace state. Prefer relative Markdown links for published documentation and verify links after cleanup. Preserve accepted policies and substantive source/provenance notes. Fix stale paths and distinguish generated reports from maintained narrative documentation.

## 3. Established comment conventions

The user's earlier tracked AGENTS.md was inspected read-only during planning. It contains the following conventions, which apply to this milestone:

- Explain scientific reasoning and why code exists, not merely what a line does.
- Keep functions focused and code readable; avoid unnecessary abstraction.
- Use NumPy-style docstrings and type hints where practical.
- Every public function documents purpose, Parameters, Returns and Raises where applicable.
- Use this major-section header style:

```python
# =============================================================================
# Section Title
# =============================================================================
```

Apply meaningful module/function documentation throughout maintained code, including private helpers when their scientific logic or failure handling is nonobvious. Explain species/identity policies, complex completeness, proxy handling, evidence aggregation, deterministic keys, transaction/recovery logic and format conversions near the implementing code. Do not add boilerplate docstrings, fabricate exception guarantees, annotate every obvious line or fragment short functions with decorative headers. Keep function signatures and behavior unchanged unless a specific necessary correction is documented and tested.

Create/update a concise current AGENTS.md that records these recovered conventions and actual paths/policies. The obsolete instruction to reproduce everything from data/received must not be restored; current sources are data/sources, originals are data/historical, and there is a separate pinned annotation dependency where used. Do not bring back contradictory old architecture.

## 4. Cleanup and GitHub preparation

Inventory tracked/untracked files, sizes and references before deleting anything. Likely disposable candidates are regenerable render previews, failed-export remnants, logs, bytecode caches and obsolete scratch files in .build-work or .normalization-work. Their names alone do not prove they are disposable: inspect contents and script references. If a required helper lives there, move it to an appropriate maintained location and update references before cleaning the scratch directory.

Remove only verified disposable artifacts within the project, after confirming no active process or recovery state depends on them. On Windows, resolve each recursive-delete target to an absolute path and verify it stays within the intended workspace; use native literal-path operations without cross-shell string-built deletion commands. Do not remove active lock/backup recovery data blindly. Keep a concise cleanup record of removed categories/paths and why they were unnecessary.

Preserve data/historical, all raw source assets, acquisition log, authoritative intermediates/manifests, final databases/support tables, accepted policies, useful handoffs, tests, and the local Obsidian configuration. Do not delete the working .venv merely to tidy the repository; ignore it. Consolidate duplicate/superseded planning notes only after preserving unique information and fixing links, with no loss of decisions. A clearly labeled archive/index is preferable to indiscriminate removal.

Create an appropriate root .gitignore for environments, caches, temporary staging/render files, credentials and personal Obsidian state. Do not blanket-ignore all data or manifests. Local preservation and public publication eligibility are separate decisions.

Check tracked files as well as untracked ones for accidental secrets/personal configuration without displaying secret values. Inspect relevant Git history for publication hazards; report historical issues without rewriting history or force-pushing. Check large files and current GitHub limits using official documentation. Recommend or configure an appropriate storage strategy only as necessary; do not install Git LFS or migrate history without a demonstrated need. Report repository and largest-file sizes.

Review source-data redistribution terms, including derived outputs, before claiming public-upload readiness. Existing documented concerns include ConnectomeDB's conflicting download-page/software/data terms, heterogeneous academic OmniPath terms and GtoPdb licensing. Verify current official terms and state unresolved conditions without inventing permissions. Preserve restricted/uncertain data locally; define an explicit public-file inclusion plan and identify what must be withheld pending resolution. Document how any withheld files can be acquired legitimately. Do not assign a blanket code license to third-party data, and do not choose a new code license on the user's behalf if their intended license cannot be established. These issues must not block completing unaffected documentation and cleanup.

Do not create a remote, commit, push or publish. The requested outcome is a prepared working tree and an honest upload-readiness report, not an external release.

## 5. Verification and provenance after commenting

Run the existing relevant tests and documentation/schema/link checks. Check representative CLI help and documented commands. If code comments/docstrings change implementation hashes used by manifests, handle that deliberately: regenerate relevant derived manifests/validation through supported commands, and verify biological records and semantic counts are unchanged. Do not hand-edit hashes to make validation appear successful or discard checks to avoid rebuilding. Generated ZIP metadata may differ; compare semantic outputs rather than assuming XLSX byte equality. Raw/historical data must remain byte-identical.

If a correctness issue is discovered, document and test it separately from comment-only work; do not change accepted biological policies silently. Use the actual current build as the baseline, not the old workbook. The last reported primary/companion totals were human 12,091/1,999 and mouse 9,585/998, with all 161,579 assertions traceable; investigate any semantic difference.

## Deliverables

- Complete, verified field guide and script guide in the Obsidian vault.
- Current README, commenting conventions and effective in-code comments/docstrings.
- Cleaned working tree, suitable ignores, preserved scientific data and tests.
- docs/Repository readiness.md: setup/validation results, file sizes, cleanup actions, public inclusion plan, licensing/access/dependency blockers and exact remaining steps before upload.
- A concise final response linking the guides and readiness report, listing checks performed, confirming whether biological outputs stayed unchanged, and clearly separating completed preparation from any unresolved publication blockers.
