# Code-docs release candidate

Accession: **RC005** · Assessment date: **2026-09-21** · Handoff: **005 only**

**Decision: a conditional code-and-documentation candidate is identifiable, but neither the current working tree nor its existing history is cleared for a public push.** This assessment proposes files and decisions; it does not prepare/export a publication tree. No scientific rebuild is needed to deliver this assessment.

## Boundary and evidence

One deliverable: this note. Moderate effort, with unresolved ownership and fixture provenance; no exact cost estimate is claimed. Verification was limited to current candidate text/path review, existing reports, relative links, small implementation-file hash comparisons and bounded Git status/index/recent-history inspection. Full-build/export allowance: **zero**. No builds, exports, renders, tests, dependency installation, network/legal research, historical-blob scan, staging, commits, remotes, publication or history changes were performed. Scientific data and existing unrelated changes remain untouched.

The older [Repository readiness](Repository%20readiness.md) is background evidence, not an instruction to resume 004. Its blanket description of tests as synthetic and its suggestion to publish AGENTS.md are superseded for this candidate. Its final verification section remains unfinished.

## Exact proposed public paths

This is an explicit **prospective allowlist of 27 existing paths**, not a wildcard or authorization to copy their current bytes. All require the owner's code/documentation rights and license decision. Conditions below must be satisfied before a path is included. In particular, **current source-derived examples are withheld**, even where a cleaned version of the containing script is proposed. No LICENSE is currently selected or included: a separately approved LICENSE must be added in the next accepted task.

| Proposed path | Purpose | Condition before public inclusion |
|---|---|---|
| `.gitignore` | Local artifact/credential exclusions | Keep `/AGENTS.md` and vault/environment exclusions; replace the reference to the withheld readiness note with public README guidance. Ignore rules are not the allowlist |
| `README.md` | Public entry point | Apply the precise public-copy edits below; current data/report links and local-release counts must not ship unchanged |
| `requirements.txt` | Standard-library downloader prerequisite | Retain its narrow downloader scope; it does not install the full table workflow |
| `requirements-normalization.txt` | Direct table-workflow package pins | Describe prerequisites, not proof of a reproducible clone |
| `requirements-validated.txt` | Previously recorded full Python package resolution | Label as historical tested resolution for Python 3.12; not a cross-platform guarantee or new validation result |
| `config/annotation-reference.json` | Relative names and hashes of three external reference assets | Contains no annotation rows or personal absolute paths; confirm permission to publish this provenance metadata. Do not bundle reference files |
| `docs/Accepted database policies.md` | Scientific scope and interpretation policy | Publish an owner-approved copy; remove the conversational A59–A62 reference in its introduction, preserving substantive policies and the local authoritative original |
| `docs/Script guide.md` | Generic interfaces, prerequisites and side effects | Remove withheld-file links, internal milestone instructions and blanket synthetic-test claims; separate private-data workflows from public-copy checks |
| `scripts/download_sources.py` | Source acquisition and transaction handling | Source code only; no downloaded files or credentials. Retain TLS protections |
| `scripts/source_registry.py` | Provider discovery, citations and access constraints | Retain access/redistribution caveats; discovery URLs do not establish rights to distribute retrieved data |
| `scripts/normalization_core.py` | Schemas and species-preserving normalization primitives | Include implementation, not normalized rows; ownership/attribution confirmation applies |
| `scripts/source_normalizers.py` | Source-format adapters | Field names and interpretation logic are code interfaces; no raw fixtures/assets included. Do not claim independent ownership merely from their project location |
| `scripts/normalize_sources.py` | Local normalization entry point | Document dependency on authorized original files and acquisition metadata; retain separate workflow |
| `scripts/normalization_report.py` | Generated-report template | **Current version withheld pending a generic public template.** Remove embedded source-specific example interactions, observed counts and frozen release statements; preserve interfaces and computation. Do not copy current illustrative records into the public template |
| `scripts/validate_normalization.py` | Data-dependent integrity/repeat checks | Not a public-clone smoke check: it requires local data, and `--repeat` regenerates normalization/report and invokes tests |
| `scripts/database_identity.py` | Same-species canonical identity and definitions | External annotation/source lookups remain prerequisites; no reference data or orthology conversion added |
| `scripts/database_build.py` | Accepted-policy assembly | Requires policy, source/intermediate manifests and local data. Publishing implementation does not publish or validate the datasets |
| `scripts/database_export.py` | Parquet/Excel writing and comparison | Explain optional host-specific preview runtime; do not execute it during candidate preparation |
| `scripts/build_databases.py` | Full scientific build entry point | Not an installation check: it runs tests, exports and parity validation. Future use needs separately authorized inputs/execution |
| `scripts/export_database_workbooks.mjs` | Optional sample PNG renderer | Label optional and dependent on `@oai/artifact-tool`; retain no samples or rendered images |
| `scripts/validate_database_release.py` | Existing-release checker | Data-dependent; publishing the code does not certify the current output files |
| `scripts/generate_field_guide.py` | Data-driven guide generator | Supporting field-guide configuration/data are withheld; label unavailable in the initial public copy without separately supplied authorized inputs |
| `scripts/generate_manifest_guide.py` | Local manifest reference generator | Requires withheld manifests and field-guide metadata; not a standalone public-copy check |
| `scripts/validate_documentation.py` | Full-workspace docs/reference checks | Its entry point requires external annotations and the full local documentation set. Do not advertise it as the first public-copy check; no redesign proposed |
| `tests/test_download_sources.py` | Acquisition regressions | Reviewed constructed A/B payloads, example.org URLs, dummy hashes and mocked transport; real provider names/paths are interface references, not a supplied database extract |
| `tests/test_build_databases.py` | Identity/policy/export regressions | Reviewed constructed A/B/C identities and temporary fixtures. Contains a tiny Excel-writing test; **do not execute it under a zero-export task** |
| `tests/test_documentation.py` | Location override and reference-pin regressions | Reviewed mocked resolver and locally constructed `fixture`/`changed` bytes; no reference rows embedded |

This is a source-code release proposal, not a standalone scientific-data distribution. A clean copy using this list will not reproduce the databases without the explicitly missing inputs. Documentation-generation tools can be published as maintainer tools with their prerequisites clearly marked; missing inputs must not be hidden by advertising their execution as a smoke check.

### Fixture and template provenance finding

`tests/test_normalize_sources.py` is **not** on the allowlist. It builds small in-memory tables, but includes real biological identifiers, publication IDs, provider-specific complex labels, pathway values and a source release line. Its header explicitly says fixtures use supplied source columns and record semantics. In-memory construction alone does not establish independent synthetic provenance. Without reconstructing its provenance or doing legal research, withhold it pending owner confirmation or a separately reviewed synthetic replacement.

Likewise, `scripts/normalization_report.py` embeds real source examples and observations, rather than merely computing all examples from private inputs. The current bytes must remain local until a generic public variant is approved. This is a content/provenance condition, not a legal conclusion that every isolated biological identifier is protected.

## Withheld material: preserve locally

| Category / exact notable paths | Why withheld |
|---|---|
| All of `data/sources/`, `data/interim/`, `data/processed/`, `data/historical/` | Original/derived scientific data, evidence, examples and manifests; redistribution unresolved; some manifests expose local paths |
| External annotation assets and their originating project | Separate ownership/access dependency; no asset copying or reconstruction authorized |
| `config/field-guide.json`, `config/field-guide-introduction.md`, `config/source-field-mapping.md` | Observed vocabularies, source-derived examples/counts and detailed source mappings; not automatically generic documentation |
| `docs/Database dictionary.md`, `docs/Manifest reference.md`, `docs/Final database build.md`, `docs/Source normalization and decisions.md` | Generated from actual local data/provenance; outside the initial generic-docs candidate |
| `tests/test_normalize_sources.py`; current source-example portions of `scripts/normalization_report.py` | Fixture/template provenance conditions above |
| `docs/Source acquisition.md`, `docs/Normalization usage.md`, `docs/initial-assessment.md`, `docs/Repository readiness.md`, `docs/Welcome.md`, `docs/Handoff index.md`, `docs/audits/` | Local acquisition/results/history/workflow context and links to withheld material; do not expand this milestone into redaction of every note |
| This assessment; `docs/handoffs/`, `handoffs/`, `AGENTS.md`, `docs/.obsidian/` | Local review, handoff and user-specific instructions/state; not proposed public content |
| `.venv/`, scratch/cache/editor directories, credentials, `.git/` | Local environment, potentially private state and unsuitable inherited history; never copy by wildcard |
| Every path not explicitly allowlisted above | Default exclusion, including pre-existing tracked deletions; no restoration or deletion undertaken |

The old readiness note's terms findings remain unresolved: ConnectomeDB's conflicting statements, heterogeneous academic OmniPath restrictions, GtoPdb database/content obligations and other source/upstream permissions. They were **not re-researched today**. Withholding data reduces this candidate's scope; it does not resolve data licensing or clear source-derived fixtures/templates.

## Minimal public README/setup edits needed later

1. Describe a code-only release. Remove the local database-count table and source-assertion totals from the public copy; remove download links to the four withheld primary data artifacts. State that datasets are acquired separately under their providers' terms.
2. Keep links only to included `docs/Script guide.md`, `docs/Accepted database policies.md`, `config/annotation-reference.json`, dependency files and source code. Remove links to the field guide, generated build report, acquisition/normalization notes, readiness note and handoff index. Do not delete the local originals.
3. Keep Python 3.11+ for the table workflow and Python 3.10+ for the downloader, with Windows versus Unix environment paths. Mark the Python 3.12 package resolution as a prior result; do not promise every OS/version works. No environment creation is needed for candidate preparation.
4. Clearly separate installation from scientific execution. `validate_normalization.py --repeat` regenerates data, `build_databases.py` exports and runs tests, and guide/documentation validators require withheld inputs. Do not present these as routine verification of a fresh public clone.
5. Describe `--annotation-dir` as an explicit authorized location containing `manifest.json`, `Parquet/human.parquet` and `Parquet/mouse.parquet`. The reference metadata pins the required bytes. No stable public retrieval command or entitlement to redistribute those files is established. The sibling-directory default is a convention, not a bundled dependency.
6. Retain `--skip-previews` guidance for any separately authorized future build. `--node` changes the executable only; the optional artifact package location remains host-specific. Do not install/copy the host runtime into the public tree.
7. Explain the recorded LRdb TLS limitation and GtoPdb authenticated-access limitation. There is no maintained generic manual-import CLI or completed GtoPdb authenticated refresh adapter. Do not promise automatic acquisition of every required source, invent credentials or recommend disabling TLS.
8. In the public Script guide, remove links to withheld acquisition/readiness/test files and remove the blanket all-tests-synthetic claim. Document the omitted fixture set and reduced candidate scope. Historical results from 53 tests do not become results for the selected public test subset. Remove conversational policy-introduction references and internal workflow-note references from the selected public copies.

Current links are locally valid but not candidate-valid: README has 14 relative-link occurrences, with 10 distinct targets withheld; Script guide has 26 occurrences, with three distinct targets withheld. Accepted policies has no relative links. The intended candidate must be checked against its allowlist, not the fuller local workspace.

## License, ownership and history decisions

**L1 — Code/documentation license and rights holder: unresolved.** No selected license is present. The existing audit records a zero-byte historical LICENSE. Confirm the intended copyright holder, contribution ownership and authority to publish this lab-related work; the lab/project directory name is not proof of institutional ownership or of personal ownership. Institutional/coauthor approval may be needed, but its requirement was not established here. The user must select the license; no default has been chosen.

**L2 — Fixtures and source-derived template text: unresolved.** Keep the uncertain normalization test withheld. Approve a generic report-template variant, or establish the relevant rights/provenance in a separate task. Do not turn this into blanket data redistribution clearance.

**H1 — Recommend a new clean, allowlisted publication tree.** Current tracked paths include legacy `data/processed/genes.csv`, `ligand_receptor.csv`, `ligand_receptor.parquet` and a notebook, despite their working-tree deletions. The bounded recent log shows the original database-upload commit. Prior audit records also include personal paths and scientific assets in reachable/reflog-referenced history; that combined scope must not be mistaken for proof every listed blob is on the current branch. Even the present tracked inventory is enough to avoid casually publishing existing history.

AGENTS.md is now locally ignored and staged for index removal; that is an existing user change, preserved here. It does not remove earlier history. Do not push this repository simply after adding new files. Prefer a separately accepted task that creates an explicitly allowlisted copy without `.git`, data, handoffs or user instructions; a fresh history can be considered later. **No copy/export, Git initialization or history rewrite was executed here.**

## Checks performed and limits of prior validation

- Reviewed 28 bounded text files: 16 scripts, four test modules, three dependency files, two generic documentation candidates, README, .gitignore and annotation-reference metadata (338,292 bytes total). The largest reviewed file is `scripts/source_normalizers.py`, 34,653 bytes. Removing the uncertain normalization test leaves the 27 prospective paths above. This is not a full code/security or ownership audit.
- Candidate text screening found no matches for the checked token/private-key/credential-URL/long-secret-assignment/personal-home-path patterns. No sensitive values were printed. A bounded pattern screen is not proof of absence of all secrets. Relative sibling paths and `Path.home()` runtime assumptions were reviewed separately.
- Inspected Git status, tracked paths, at most three recent commit summaries and the existing audit record. No historical blobs were rescanned. Existing staged and unstaged changes were preserved.
- Read existing normalization/build validation metadata and prior CLI-help results. Compared **only eight small implementation-file hashes**: all three recorded normalization hashes and all five recorded build hashes match current bytes; per-source normalization implementation maps also agree. No covered implementation-byte drift was found in that limited comparison.
- The existing normalization validation records 161,579 records, 53 passing tests, repeat byte/semantic determinism and 55 protected files unchanged. The existing build manifest records success, 53 tests, repeat semantic determinism, two 12-sheet workbooks and 6,440,884 compared cells; previews were explicitly skipped. These are **recorded prior outcomes**, not checks executed today.
- The manifests do not hash every test, dependency, documentation or helper file. The historical CLI-help record has no code-byte binding. Matching the eight implementation hashes does not establish current test-suite results, dependency identity, output integrity or public-copy behavior. Output bytes, annotation bytes, baseline semantic equality and full post-build release validation were not rechecked. The unfinished 004 readiness/report work remains unfinished rather than silently resumed.
- The public copy will omit data/configuration and at least one test file, and may contain an edited report template. Prior scientific validation must not be represented as validation of that future candidate. Conversely, an uncompleted broad scientific audit need not be repaired to assess a code-only candidate honestly.

## Small next handoff proposal — not dispatched

**Deliverable:** prepare one reviewable clean code/docs candidate directory from the approved exact allowlist, after L1/L2/H1 decisions. Do not create a remote or publish.

**Effort:** low to moderate; uncertainty is restricted to approval/ownership and whether report-template text can be generalized without changing computation. If that requires wider implementation work, stop with a checkpoint.

**Scope:** selected-file copying into a new location without inherited `.git`; owner-supplied LICENSE; only the public-copy README, Script guide, policy introduction, .gitignore reference and generic normalization-report prose edits specified above. Keep the source repository's scientific files, accepted policies and user changes intact. Leave the normalization test excluded unless separately cleared.

**Named checks:** exact allowlist/path inventory (including no `.git` or hidden data); bounded text/credential/personal-path screening; relative links resolved inside the candidate only; selected Python source syntax parsing without import/execution or bytecode writes; review that any template edit changes explanatory text only. No test suite or scientific command execution is needed for this preparation step. Permit one affected lightweight check rerun for a clear defect; otherwise return a checkpoint.

**Limits:** zero database builds, exports, renders, downloads, environment creation, full suites, legal expansion, historical scans, history rewriting or automatic follow-on work. A separate publication-tree copy is authorized only if the user accepts this proposed next task. Do not treat this note as that authorization.

**Stop:** return the exact copied file list, applied edits, candidate-level check results and remaining limitations. No commit, push or publication. If stopped, cancel owned active and queued work and preserve partial files.

**Required checkpoint decisions:** Which code/documentation license and copyright holder should be used? Is institutional/coauthor approval required or already obtained? Is a separate clean publication tree acceptable, with uncertain fixtures withheld and a generic report template prepared as described?
