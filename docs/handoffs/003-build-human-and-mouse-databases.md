# Codex handoff 003 — Build human and mouse ligand–receptor databases

Status: ready for implementation; not executed.

## Objective

Implement and run an offline final-build step from the normalized sources. Produce separate human and mouse master databases as Excel and Parquet, with required nonprotein/proxy companion tables, review tables, evidence and complex membership. Apply docs/Accepted database policies.md, which records the user's decisions following N01–N04. Do not ask the user to approve these policies again.

## Inputs and preservation

Workspace: `C:/Users/aweyr/OneDrive/Documents/Cheng-Lab/Tool-Development/ligand-receptor-database`.

Read applicable instructions, current Git status, docs/Accepted database policies.md, docs/Normalization usage.md, docs/Source normalization and decisions.md, and data/interim/manifest.json. Inspect actual Parquet schemas rather than assuming them from prose. All 16 sources have normalized records with evidence, memberships and regulators; the reported 161,579 rows are source assertions, not a final unique-pair target.

Use local validated inputs. Do not require the downloader to succeed: manual LRdb and GtoPdb imports are usable, while their automated access issues remain separate work. Preserve data/sources, its versions.txt, data/historical, existing vault settings, unrelated changes and user deletions. Do not push or publish. Avoid changing intermediates unless a verified normalization defect needs correction; document any such correction and regenerate affected checks rather than silently patching derived files.

## Build and merge

Add one simple documented command, primarily Python, and minimal additional dependencies. Avoid generalized workflow frameworks or scheduled jobs. Verify input checksums against the successful normalization manifest. Keep the output reproducible from the same inputs and policies.

Implement explicit source-record disposition rules; do not equate the intermediate candidate/review status with a final inclusion decision. Approval of inferred mouse evidence resolves that review reason only; other unresolved reasons still apply. Similarly, unknown experimental provenance alone is not an identifier/species failure. Keep evidence-provenance uncertainty distinct from unresolved endpoint identity or direction.

Primary eligibility requires established ligand/receptor roles, human or mouse species compatible on both endpoints, gene-encoded endpoint identities and complete interpretable complex definitions. Retain eligible source-defined interactions lacking pair-level references, with evidence limitations exposed. Do not require new manual literature curation of every pair. Put explicitly putative/unverified-interaction claims in review unless a separate eligible source assertion supports the pair; keep the weak assertion separately traceable rather than upgrading its evidence.

Preserve protein complexes as complete entities, including required membership, source definitions and known stoichiometry. Keep CellChat regulators separate. Leave unresolved alternatives and incomplete complexes in review. Do not infer completeness simply because some membership rows exist. Do not flatten complexes into Cartesian products. Gene-pair projection is out of scope for this milestone.

Construct canonical species-aware endpoint and interaction IDs for cross-source merging. Source-local semantic_key contains a source ID and is not a cross-source deduplication key. Prefer stable identifiers with authoritative same-species mapping. Source-specific complex names are not evidence of equivalence; compare resolved members, roles and known stoichiometry. Preserve unknown stoichiometry and do not silently merge incompatible definitions. Use source lookup tables first; the existing sibling annotation resource may be used only for demonstrated same-species mapping needs, recording its version/checksum. No new annotation download or orthology conversion. Ambiguous aliases must not be mapped to the first hit. If only an unverified symbol is available, document conservative matching rules and do not imply authoritative harmonization.

Collapse repeated pathway, assay and resource-membership records only at the final interaction-view level, preserving links to every contributing raw record. Keep source-specific sign, direction and evidence assertions. Do not transfer a PPI sign to a reversed LR relation or turn a missing/false stimulation flag into inhibition. Summaries must distinguish source support counts from distinct publication counts; neither is an independent-replication score. Do not invent confidence scores.

For Dimitrov, use LIANA consensus as its contribution; retain constituent membership as provenance, not additional independent Dimitrov support. Unresolved or excluded records matching an eligible pair from another source must not silently become eligible supporting evidence.

## Companion and review handling

The nonprotein/proxy companion is required for each species. Include eligible endogenous nonprotein signaling and explicit source-defined proxies with distinct molecule and proxy identifiers, dependency roles and species. Retain proxy-only assertions with a clear missing-product annotation if their proxy role is established, rather than inventing a molecule. Uncertain proxy roles belong in review. Include complete complex receptors when applicable. Keep synthetic/nonendogenous drugs and unrelated pharmacology out, with auditable reasons.

Review all remaining direction, identity, species, complex and scope flags. Do not classify missing species as the target's species, split multispecies labels into new pairs, or convert species. Maintain a shared review output for mixed/cross/unknown species so records are not forced into either species workbook. Species-resolved review entries can be included in the appropriate workbook. Retain explicit exclusions and reason codes, either in this review table with a disposition field or a separate audit table if necessary.

Address known source issues with available definitions: OmniPath mouse LR orientation is unresolved; do not include all such edges automatically. Pavlicev has source-level proxy uncertainty without per-row classification; do not include all rows as proteins or classify all as proxies. GtoPdb has synthetic ligands, multiple measurements, multispecies peptides and incomplete companion metadata. Resolve deterministically where local evidence permits; otherwise retain in review and report counts. Missing companion metadata need not block other sources or trigger unsolicited downloads.

## Outputs

Use data/processed for new outputs; the supplied originals remain in data/historical.

- Ligand-Receptor-Human-DB.xlsx and Ligand-Receptor-Human-DB.parquet.
- Ligand-Receptor-Mouse-DB.xlsx and Ligand-Receptor-Mouse-DB.parquet.
- Clearly named companion/review/evidence/membership/regulator Parquet tables needed to retain the same information in machine-readable form.
- One small build manifest containing input hashes, policy/schema/implementation versions, output hashes, counts and validation summary. Keep versions.txt as the single acquisition log; do not duplicate it.

Each workbook's primary sheet is Ligand-Receptor. Add concise clearly labeled sheets for nonprotein/proxy interactions, review entries, evidence, complex membership, regulators where applicable, and a short Readme describing scope, provenance labels and joins. Shared cross-species/unknown review records may be delivered separately as a clearly documented review file rather than duplicated in both workbooks. Use actual data volume to avoid unnecessary sheets, but do not omit the required companion or lose supporting relationships.

Keep the master easy to read: ligand and receptor display labels, stable entity/interaction IDs, species, entity types, sources, evidence summaries, provenance and direction/sign limitations. Preserve compatibility with the historical column meanings where accurate, without forcing complexes or missing signs into misleading scalar gene fields. Define exact columns after inspecting the normalized schema. Store identifiers as text. Freeze headers, enable filters and set sensible widths. Document how to join support tables. Do not truncate long evidence silently to fit Excel limits; use linked evidence rows.

Export Excel and Parquet from the same canonical tables. Document reversible list/nullable-value serialization where Excel needs text. Generate a minimal dictionary in the vault; do not require users to read implementation code to interpret columns.

## Validation and delivery

Test same-species identity mapping, cross-source duplicates, incompatible complex membership/stoichiometry, regulator separation, overlapping aggregate provenance, conflicting signs, unknown species, source-derived mouse evidence, enzyme proxies and failed/stale inputs. Check that every normalized record has a documented final disposition and traceability, including many-to-one merged records; counts must reconcile without equating assertions to unique pairs.

Validate IDs and joins, complex completeness rules, evidence retention, no cross-species conversion, and no silent source omissions. Confirm Excel/Parquet semantic parity, readable workbook layout and repeat-build semantic determinism. Preserve previous good outputs on failed builds and report failure rather than a complete release. Do not require XLSX byte identity if ZIP metadata changes, but compare data semantics.

Create docs/Final database build.md with the run command, output links, source/species contribution counts, merged primary/companion/review totals, applied policies, unresolved limitations and validation results. Clearly distinguish accepted provider-inferred evidence from verified native experimental support and unknown provenance. Report unresolved records rather than calling the database biologically validated. Do not run a historical reconstruction or make historical overlap a release criterion.

Deliver the implemented command, final files, manifest, documentation and test results. Summarize remaining limitations and any consequential unexpected choices; do not reopen approved N01–N04 decisions or add unrequested features.
