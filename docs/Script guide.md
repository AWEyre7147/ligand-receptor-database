# Script guide

Run commands from the repository root using the environment's Python. Acquisition requires Python 3.10+; normalization and final assembly require Python 3.11+ and the dependencies in [requirements-normalization.txt](../requirements-normalization.txt).

## Workflows

```powershell
# Network access: check/download provider originals.
python scripts/download_sources.py
# Offline: normalize verified sources, or select one with --source.
python scripts/normalize_sources.py
# Offline: routine final assembly and export.
python scripts/build_databases.py --annotation-dir "../gene-annotation-resources/annotations"
```

Do not download sources merely to rebuild the existing release. LRdb and GtoPdb can require authorized manual downloads; retain their original bytes and record versions in the acquisition log. Never disable certificate checks or put credentials in files or URLs.

The annotation directory must contain the exact `manifest.json`, `Parquet/human.parquet` and `Parquet/mouse.parquet` pinned by [annotation-reference.json](../config/annotation-reference.json). Only same-species identity fields are read. No orthology or enrichment columns are used.

## Maintained code

| File | Responsibility |
|---|---|
| [download_sources.py](../scripts/download_sources.py) | Provider acquisition, checksums, atomic source replacement and acquisition metadata. `--source` selects providers. |
| [source_registry.py](../scripts/source_registry.py) | Official resource definitions, discovery, versions and citation/terms links. |
| [normalization_core.py](../scripts/normalization_core.py) | Typed source records, evidence, memberships and regulators; raw values and uncertainty remain traceable. |
| [source_normalizers.py](../scripts/source_normalizers.py) | Provider-specific parsing and interpretation. |
| [normalize_sources.py](../scripts/normalize_sources.py) | Offline per-source normalization, validation and transactional intermediate replacement. |
| [normalization_report.py](../scripts/normalization_report.py) | Optional diagnostic report for `normalize_sources.py --report`; written to the local ignored archive. |
| [validate_normalization.py](../scripts/validate_normalization.py) | Intermediate schemas, keys, counts, hashes and joins. `--repeat` explicitly reruns normalization. |
| [database_identity.py](../scripts/database_identity.py) | Same-species identities, complete complexes, peptide/proxy distinctions and mapping failures. |
| [database_build.py](../scripts/database_build.py) | Accepted scientific policies, canonical tables, evidence retention and integrity checks. |
| [database_ids.py](../scripts/database_ids.py) | Deterministic release-local readable IDs and consistent final foreign keys. |
| [database_excel.py](../scripts/database_excel.py) | Template-backed Excel projection, accession header aliases, readable list display and streaming semantic hashes. |
| [database_export.py](../scripts/database_export.py) | Complete Parquet exports, streaming Excel writing and projection parity validation. |
| [build_databases.py](../scripts/build_databases.py) | Stage, validate and promote the complete processed outputs and build manifest. Diagnostic build report stays in the ignored archive. |
| [export_database_workbooks.mjs](../scripts/export_database_workbooks.mjs) | Optional bounded layout previews only. Requires the separate Node/artifact runtime; ordinary builds do not use it. |
| [generate_field_guide.py](../scripts/generate_field_guide.py) | Explicitly generate the field dictionary from curated config and actual schemas. `--check` compares without writing. |
| [validate_database_release.py](../scripts/validate_database_release.py) | Independent output/input/implementation hashes, joins and source-retention validation. |
| [validate_documentation.py](../scripts/validate_documentation.py) | Reference pins, active-document links and public-function documentation. Archived notes are excluded. |

## Output contract

Excel uses [the approved templates](../data/templates/manifest.json): Ligand-Receptor, Nonprotein-Proxy, Entities, Complex-Members and Regulators. Template checksums are recorded as build inputs. `gene_accession` is a display alias for canonical `gene_id`. Molecular/source identifiers remain in canonical identity and provenance; there is no separate product-accession column.

Excel lists use `; ` display separators and missing values are blank. Exact values and list boundaries remain in Parquet. Literal strings never execute as Excel formulas. The exporter fails on values exceeding Excel's cell limit rather than truncating them. Excel Regulators includes accepted primary/companion relationships; full audit records remain in Parquet.

IDs use at least six digits with prefixes `LRI`, `ENT`, `MEM`, `REG`, `CDF`, `ANN`, `AST`, `EVD` and `SCX`. Numbering spans the complete build before species partitioning. Identical inputs produce identical numbering, but later releases may renumber records. Cite the ID together with its build manifest. Original normalized record/evidence keys and provider accessions remain in Parquet.

## Verification

Routine builds check inputs, schemas, same-species identities, scientific policy, accounting, references, Parquet read-back and successful workbook writing. They do not repeat assembly or exhaustively compare every Excel cell.

```powershell
python scripts/build_databases.py --release-verification --annotation-dir "../gene-annotation-resources/annotations"
python scripts/validate_database_release.py
python scripts/generate_field_guide.py --check
python scripts/validate_documentation.py
```

Release verification is an explicit expensive pass. Optional `--previews` requires release verification and the separate rendering runtime. Do not refresh provenance by hand-editing hashes. Generate the field dictionary explicitly after reviewing vocabulary/schema changes; the builder never overwrites it.

Focused test modules are `test_download_sources.py`, `test_normalize_sources.py`, `test_build_databases.py`, `test_database_ids.py`, `test_database_excel.py` and `test_documentation.py`. Run a selected module with `python -m unittest discover -s tests -p test_database_excel.py -v`, for example.

## Recovery and local files

Acquisition, normalization and building use locks and staged replacement. Inspect `.download.lock`, `.normalize.lock`, `.build-work/build.lock` and any source/intermediate/processed backup before removing it. Never update sources concurrently with normalization or building. Close Excel workbooks before replacing outputs. The previous processed directory is restored on ordinary promotion failure.

Source originals, historical inputs, manifests and review records are retained. Environments, caches, intermediates, archived documents and local recovery work are ignored. Configuration is retained because annotation pinning and the curated field guide depend on it. No installable Python package is introduced by this workflow.
