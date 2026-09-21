# Final database build

Offline build applying [Accepted database policies](Accepted%20database%20policies.md) N01–N04. All 16 sources have a documented disposition. Original source assertions remain traceable; these outputs do not certify biological validation.

| Species | Primary interactions | Nonprotein/proxy interactions | Review assertions | Excluded assertions |
|---|---:|---:|---:|---:|
| human | 12,091 | 1,999 | 4,527 | 73 |
| mouse | 9,585 | 998 | 4,525 | 4 |

| Species | Primary interactions with complexes | Distinct encoded-peptide ligands in primary interactions* | Primary interactions with unverified symbols | Companion ligand types |
|---|---:|---:|---:|---|
| human | 2,548 | 261 | 32 | 1,999 nonprotein_proxy |
| mouse | 1,027 | 12 | 63 | 998 nonprotein_proxy |

*Peptide count here is distinct ligand entities, not interaction rows. The current companions contain source-defined proxies; no molecule-only GtoPdb assertion passes all endogenous, identity, direction and same-species eligibility checks. Missing product identifiers are retained explicitly, not invented from proxy names.

All **161,579 normalized assertions** reconcile: 3,000 companion, 22,244 excluded, 94,388 primary, 30,736 provenance_only, 11,211 review. These are source records; primary/companion totals above are merged interactions.

## Files and command

- [Human Excel](../data/processed/Ligand-Receptor-Human-DB.xlsx) and [Human Parquet](../data/processed/Ligand-Receptor-Human-DB.parquet).
- [Mouse Excel](../data/processed/Ligand-Receptor-Mouse-DB.xlsx) and [Mouse Parquet](../data/processed/Ligand-Receptor-Mouse-DB.parquet).
- `Human-*` and `Mouse-*` Parquet files mirror every companion/support/readme worksheet. `Shared-Review`, `Shared-Assertions` and `Shared-Evidence` retain species-incompatible or unknown assertions separately.
- [Build manifest](../data/processed/build-manifest.json) records input/policy/implementation hashes, versions, output checksums, counts and validation. See [Database dictionary](Database%20dictionary.md) for exact columns and joins.

```powershell
.venv/Scripts/python scripts/build_databases.py --repeat
```

Install `requirements-normalization.txt`. Workbooks use the existing openpyxl streaming writer: full-size artifact-tool XLSX export failed with `Invalid string length`. Use `--skip-previews` for a Python-only build; bounded previews use the bundled Node runtime and `@oai/artifact-tool`; `--node` can select that executable. No additional Python dependencies, downloader, new annotation download or species conversion runs. A complete release is staged and validated before replacing processed outputs. Failure preserves the prior release; unrelated processed files are copied through. A stale backup/lock requires inspection rather than automatic deletion.

## Source contributions

Counts below are distinct eligible interaction IDs per source. A pair may appear in several source rows; the columns must not be added as unique biological pairs. LIANA constituent memberships are retained as provenance only.

| Source | Human primary | Mouse primary | Human companion | Mouse companion | Review | Excluded | Provenance only |
|---|---:|---:|---:|---:|---:|---:|---:|
| cellcall | 1,448 | 934 | 0 | 0 | 54 | 0 | 0 |
| cellinker | 3,737 | 3,218 | 0 | 0 | 30 | 0 | 0 |
| omnipathppis | 4,548 | 0 | 0 | 0 | 6,415 | 0 | 0 |
| dimitrov | 4,511 | 0 | 0 | 0 | 109 | 0 | 30,736 |
| cellphonedb | 1,466 | 0 | 1,025 | 0 | 420 | 0 | 0 |
| kirouac | 398 | 0 | 0 | 0 | 238 | 0 | 0 |
| cellchat | 2,227 | 2,363 | 974 | 998 | 21 | 0 | 0 |
| connectomedb | 3,546 | 3,224 | 0 | 0 | 8 | 0 | 0 |
| italk | 2,547 | 0 | 0 | 0 | 41 | 0 | 0 |
| lrdb | 3,614 | 0 | 0 | 0 | 21 | 0 | 0 |
| ramilowski | 2,007 | 0 | 0 | 0 | 549 | 0 | 0 |
| pavlicev | 0 | 0 | 0 | 0 | 1,006 | 0 | 0 |
| nichenet | 4,976 | 5,604 | 0 | 0 | 14 | 0 | 0 |
| gtopdb | 381 | 15 | 0 | 0 | 2,267 | 22,244 | 0 |
| celltalkdb | 3,398 | 2,031 | 0 | 0 | 2 | 0 | 0 |
| icellnet | 1,653 | 0 | 0 | 0 | 16 | 0 | 0 |

Shared outputs contain **24,326 assertions**: 180 cross_species, 349 mixed_species, 28 other_species, 23,769 unknown_species.

## Applied identity and evidence rules

- Source lookups precede same-species annotation mappings. The local annotation run `20260920T002526867731Z` is used only for identity columns (NCBI Gene, HGNC/MGI, UniProt, Ensembl, exact symbols/aliases and taxon). Its human/mouse files and manifest hashes are recorded. Orthology columns are never read. No enrichment columns are added.
- Stable identifiers map to a unique same-species NCBI Gene identity. Conflicting identifier/symbol mappings or ambiguous aliases remain review. Unmapped literal symbols use exact case-sensitive identities, carry an explicit unverified limitation, and cannot merge with stable identities without a mapping. Unverified symbols are not allowed to establish complex-member completeness.
- Complete complexes merge only on resolved members, dependency roles, known stoichiometry and incompatible assembly context. Unknown stoichiometry remains unknown. CellPhoneDB semicolon stoichiometry lists are counted only when their complete set matches endpoint members; ligand-bound assembly context otherwise stays separate. Full explicit definition lists are checked, not merely the presence of membership rows.
- Endogenous GtoPdb peptides retain their molecular ligand identity and an `encoded_by` gene relationship, preventing collapse of distinct mature peptides/proteoforms into one precursor. Receptor classes are restricted to source `gpcr`, `catalytic_receptor`, `lgic` and `nhr`; other pharmacology classes stay review. GtoPdb subunit lists can describe alternative families (e.g. BMP receptors), not obligate complexes. Receptor lists require an identical complete gene set in an explicit local non-GtoPdb complex definition, linked by `supporting_definition_ids`; single-subunit lists remain review. This tightens interpretation at final disposition without editing the normalized inputs; `Source-Members` retains their original membership assertions without endorsing their roles.
- Explicit source proxies retain their source entity identity, dependency roles and a missing-product annotation. Enzymes are never renamed as their products. CellChat regulators remain separate from complex members. Pavlicev and description-only possible enzyme proxies remain review.
- Eligible provider-derived mouse evidence is accepted and labeled inferred. Unknown provenance remains unknown. `native_reported` means a provider assertion, not independently verified experimental evidence. Per-record labels remain in Assertions even when a merged interaction has multiple labels.
- Only eligible assertions contribute to source/publication/sign summaries. Putative, excluded, unresolved and LIANA constituent assertions can have `related_interaction_id` links without becoming support. Missing references alone do not exclude an interaction. Aggregator/source overlap is exposed and not scored as independent replication.

## Unresolved limitations

| Reason (overlapping counts) | Assertions |
|---|---:|
| `N04_direction_or_interaction_scope` | 6,769 |
| `ligand_receptor_orientation_not_established` | 6,769 |
| `endpoint_species_not_single_human_or_mouse` | 2,159 |
| `N04_unknown_species` | 1,936 |
| `N03_endogenous_status_not_positive` | 1,232 |
| `N03_unclassified_proxy_possible_in_publication` | 1,006 |
| `N04_putative_interaction` | 528 |
| `unresolved_identifier` | 256 |
| `ligand:unresolved_normalized_identifier` | 234 |
| `receptor:unresolved_normalized_identifier` | 233 |
| `N04_free_text_receptor_alternatives_or_complex` | 232 |
| `ligand:ambiguous_identifier` | 231 |
| `ligand:unresolved_same_species_identifier` | 226 |
| `N04_mixed_species` | 223 |
| `receptor:unresolved_same_species_identifier` | 84 |
| `receptor:target_companion_encoding_not_unique` | 54 |
| `N03_enzyme_named_ligand_requires_review` | 45 |
| `ligand:uncertain_endpoint_type` | 45 |
| `unresolved_member_id_in_companion_table` | 44 |
| `ligand:duplicate_complex_components_without_explicit_stoichiometry` | 40 |
| `ligand:ambiguous_alias` | 37 |
| `receptor:ambiguous_alias` | 25 |
| `receptor:ambiguous_identifier` | 24 |
| `receptor:gtopdb_subunit_list_not_confirmed_obligate_complex` | 22 |
| `pharmacology_target_not_established_receptor_class` | 19 |
| `ligand:identifier_symbol_conflict` | 8 |
| `receptor:identifier_symbol_conflict` | 6 |
| `gene_encoded_ligand_unconfirmed` | 3 |
| `N04_target_is_ligand_entity` | 3 |
| `ligand:gtopdb_complex_completeness_unestablished` | 2 |
| `ligand:peptide_encoding_not_unique` | 1 |

Eligible mouse source-assertion provenance: 24,383 provider_orthology, 8,642 unknown.

OmniPath mouse orientation remains unresolved and contributes no automatic mouse support. Pavlicev S5 cannot be divided reliably into proteins and proxies using its local per-row fields. GtoPdb missing/multispecies ligand metadata is not filled from target species; synthetic/nonendogenous rows remain auditable exclusions. Source symbol aliases, incomplete complexes and conflicting metadata remain explicit. No online acquisition issue blocked this offline build.

## Validation

- 53 tests passed, including identity/species, cross-source merging, complex membership/stoichiometry, regulators, proxies, overlapping provenance, signs and stale inputs.
- Excel/Parquet parity: every exported data cell compared after reversible decoding; IDs remained text and no executable formulas were emitted.
- All normalized records have one disposition; every evidence/regulator row is retained; source totals, schemas, keys and joins reconcile.
- Repeat canonical-build semantic determinism: passed.
- Input checksums verified before and after the build. Protected input/historical/intermediate/vault snapshot: {'count': 55, 'status': 'unchanged'}.
- Workbook headers, filters, freezes and widths are checked from worksheet XML. Optional preview status: skipped by request. Long values remain available in full through Excel cells/support rows and Parquet; no evidence is truncated.
