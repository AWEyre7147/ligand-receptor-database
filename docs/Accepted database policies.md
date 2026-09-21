# Accepted database policies

Accepted following review of N01–N04 and the historical-versus-new comparison (A59–A62). These decisions belong in this persistent note, not the generated normalization report.

## Scope

Build new human and mouse databases from acquired sources, without historical reconstruction or new species conversion. Provide a primary gene-encoded ligand–receptor table, a required nonprotein/proxy companion table, and review records. Preserve original evidence and provenance. Raw and historical files remain unchanged.

## N01 — Species and evidence provenance

Include eligible provider-derived mouse interactions with an explicit inferred label. Unknown native/inferred provenance must remain unknown; it is not proof of native experimental support. Preserve per-source provenance when a merged pair has multiple kinds of support. Do not perform orthology mapping or symbol-case conversion. Uncertain, mixed and cross-species assertions remain in review until resolved from evidence.

## N02 — Complete complexes

One interaction connects complete endpoint entities. Preserve required subunits and available stoichiometry; cofactors and regulators are distinct. Do not split required complexes into independent gene pairs. Incomplete or ambiguous definitions remain in review. An optional gene-pair projection is deferred until downstream utility requirements are known.

## N03 — Nonprotein and proxy companion

Primary tables contain gene-encoded ligand–receptor interactions, including eligible protein complexes. A required companion preserves nonprotein ligands and source-defined production/transport proxies as explicitly different entity types and relationships. Do not rename an enzyme as its product. Uncertain proxy classifications remain in review. Synthetic drugs and unrelated pharmacological interactions do not become eligible merely because the companion exists.

## N04 — Uncertainty and scope

Resolve uncertainty from available source definitions where possible; otherwise keep unresolved identifiers, ambiguous direction, uncertain species and non-LR interaction classes out of the primary table with explicit review reasons. Cell adhesion is not automatically excluded if it has a well-defined ligand–receptor interpretation. Missing pair-level references alone do not exclude a source-defined interaction, but must remain visible. Source membership is not proof of independent validation.

## Evidence and presentation

Keep raw source assertions, versions and evidence traceable. Distinguish direct reference fields, database membership, dataset citations and provider summary links. Unknown stimulation/inhibition stays missing; contradictory assertions remain visible. Final counts need not resemble the historical workbook. Provide Excel for sharing and matching Parquet data for Python utilities.
