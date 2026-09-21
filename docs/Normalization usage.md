# Offline source normalization

Install Python 3.11+ and the small table readers/writers in `requirements-normalization.txt`. The acquisition downloader still uses only the standard library; these additional dependencies are for normalization. No R interpreter or source analysis packages are installed or executed.

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-normalization.txt
.venv/Scripts/python scripts/normalize_sources.py --report
```

On macOS/Linux use `.venv/bin/python`. In this Windows workspace the project virtual environment was created using the bundled Python interpreter, with existing bundled pandas/numpy/openpyxl available through system site packages. Milestone 004 also verified a separate clean environment without system site packages; see [Script guide](Script%20guide.md) and requirements-validated.txt for the tested resolution. The dependency versions are recorded in the normalization manifest. No network access is used by the normalization command and the downloader is not run. LRdb/GtoPdb manual imports are accepted only when their local bytes match the acquisition manifest, irrespective of the latest automated acquisition status.

Use `--source cellchat` (repeatable) for a focused rebuild. `--report` regenerates [Source normalization and decisions](Source%20normalization%20and%20decisions.md) from the successful per-source outputs. Do not edit decisions into that generated report; store accepted decisions in a separate vault note or handoff. Normalization preserves review records and does not treat report recommendations as approved policies.

## Outputs and schema

Each `data/interim/<source>/` directory contains:

| Table | Row meaning | Important fields |
|---|---|---|
| `records.parquet` | One original interaction/pathway/assay/membership assertion | Stable `record_key`, `semantic_key`, source file/table/row/stable ID, original endpoint labels/IDs and roles, normalized typed/namespaced endpoints, endpoint species lists, dataset species/provenance, orientation/sign, typed review/exclusion reasons and complete source interaction `raw_json`. |
| `evidence.parquet` | One typed evidence value linked to an original record | `record_key`, type, value, underlying provider and source field. PubMed, source evidence text, pathway, database record, membership, URL and patent values are distinct. |
| `memberships.parquet` | One constituent of a declared complex or proxy group | `complex_key`, member ID/label/namespace/species/order, relationship, nullable stoichiometry and exact source definition location. |
| `regulators.parquet` | One CellChat regulator-group member linked to an interaction | Original group, role (agonist, antagonist, co_A_receptor, co_I_receptor), member and species. These are not required endpoint subunits. |
| `review_examples.tsv` | Deterministic sample across normal, mouse, complex, nonprotein, excluded and unresolved records | Review-friendly scalar fields; list columns are JSON arrays. Full tables remain in Parquet. |

All four Parquet schemas are explicit and consistent across sources, including empty tables. Scalar fields are strings, species/source/reason sets are lists of strings, sign assertions are nullable booleans and member order is an integer. No broad symbol concatenation is used as a unique record identifier.

`record_key` hashes source, original file/table/row and optional stable source ID. `semantic_key` hashes source plus both typed/namespaced endpoint IDs, species sets, complex identities and normalized orientation. Keys contain no timestamps. Repeated TF/pathway rows, assays, affinity values and source memberships remain distinct original records with a shared semantic key where appropriate; there is no lossy deduplication. Distinct assertions are source-local, not a cross-source merged count. Missing labels retain source-specific identifiers/names where available; uncertain aliases are never chosen automatically.

For established LR schemas, endpoint species can inherit an explicitly species-specific dataset, with `species_basis=dataset`. Explicit endpoint species override this where supplied. GtoPdb ligand species is never inferred from its target; a missing value can be filled only by the same ligand ID in its peptide companion. Multi-species labels remain sets and do not generate rows. iTALK missing approved receptor symbols retain their source names and unknown endpoint species. No capitalization-based translation occurs.

Status meanings:

- `candidate`: no implemented review/exclusion condition was triggered. This is not biological validation or master-database inclusion approval. Unknown human evidence provenance and unverified source symbols may still be present.
- `review`: retained pending at least one explicit policy, species, direction, identity, sign or metadata decision. All known inferred mouse records and unknown-native-evidence mouse records fall here.
- `excluded`: retained for audit but explicitly outside the current human/mouse endogenous communication candidate scope (for example synthetic/nonendogenous pharmacological ligands or other target species). Other uncertainty flags may also be present.

The report's human/mouse candidate-pool counts include nonexcluded review records. Its stricter `candidate` and `review` counts are separately available in the manifest. Distinct keys can occur in both status subsets (for example consensus versus constituent LIANA membership); use the dedicated `nonexcluded_distinct_by_species` metric for their union.

The script preserves source-specific annotations instead of forcing misleading equivalences: OmniPath PPI signs do not transfer to a reversed LR orientation; GtoPdb agonism is not automatically stimulation; CellChat nonprotein classification uses its annotation rather than its unreliable neurotransmitter flag. False stimulation does not mean inhibition. Raw signs/directionality and all assay fields remain inspectable.

## Provenance and inventory

`data/interim/manifest.json` is the single derived-output provenance manifest, separate from the untouched acquisition log. It records schema/adapter version, implementation checksums, tested library versions, each source's input checksums and acquisition selection, output paths/checksums and semantic checksums, complete parsed-table inventories, row reconciliation, status/species/reason counts, limitations and examples. Inventories distinguish interaction tables from gene/protein/complex/cofactor support and workbook expression sheets. Noninteraction workbook sheet counts include their titles/headers, explicitly labeled as such; those sheets are not mistaken for interaction records.

The original source citation is dataset provenance in the manifest, never copied onto all rows as experimental support. LRdb/iTALK have no pair-level reference field. Aggregate membership remains separate from PubMed evidence. ConnectomeDB IDs extracted from provider AI-summary URLs retain a special evidence type. No summaries are fetched. Source-provided same-species IDs and lookups are sufficient for this stage; the sibling annotation resource was not used.

Source definition files remain unchanged. The additional normalization modules are `normalization_core.py`, `source_normalizers.py`, `normalize_sources.py`, `normalization_report.py` and `validate_normalization.py`. Adding a new schema or resolving a biological policy should change the adapter/schema version and be accompanied by focused tests.

## Validation and failures

```sh
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python scripts/validate_normalization.py --repeat
```

The validator independently reloads all Parquet files, verifies input/output and implementation checksums, schemas, unique record keys, row reconciliation, complex/evidence/regulator references, summary counts and semantic digests. `--repeat` rebuilds all 16 sources and compares both semantic and file-byte hashes. It also runs the tests and writes `data/interim/validation.json`, a validation result rather than another acquisition/version log.

An optional `--protected-baseline <json>` checks a pre-task mapping of paths to SHA-256, used in this implementation session to verify all pre-existing source/historical/vault files. It is not required for future builds; ordinary validation always verifies source inputs and `versions.txt` against their recorded hashes.

Each source is staged and validated before replacing its derived directory. A source failure records an error and retains the prior successful source output; other sources continue, and the command returns nonzero. Prior outputs retained after failure are not current successful normalization. A lock prevents concurrent runs. If a process is killed during promotion, inspect `.source.backup` and the committed output hashes before restoring/removing it; an unresolved backup blocks that source. A stale lock may be removed only after confirming no run is active.

This milestone produces no master database, annotation enrichment, orthology conversion, scheduled workflow or presentation workbook. Review N01, N02, N03 and the additional N04 scope items before the next master-generation handoff.
