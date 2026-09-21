# Ligand–receptor databases

Species-preserving human and mouse ligand–receptor resources assembled from 16 locally acquired providers. Original files, evidence, complete complexes, inferred mouse provenance and unresolved records remain traceable. No species conversion is performed.

| View | Human | Mouse |
|---|---:|---:|
| Gene-encoded primary interactions | 12,091 | 9,585 |
| Separate nonprotein/proxy companion | 1,999 | 998 |

The current companions contain source-defined proxies, not molecule-only coverage. All 161,579 original source assertions have a final disposition. These are curated computational views, not independent biological validation.

Start with the [human workbook](data/processed/Ligand-Receptor-Human-DB.xlsx), [mouse workbook](data/processed/Ligand-Receptor-Mouse-DB.xlsx), or typed [human](data/processed/Ligand-Receptor-Human-DB.parquet) / [mouse](data/processed/Ligand-Receptor-Mouse-DB.parquet) Parquet. Data links require the local authorized datasets; data are not cleared for public distribution.

## Setup and separate workflow stages

Python 3.11+ is required for the table workflow (tested in a clean Python 3.12 environment). Run from the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-normalization.txt
.venv/Scripts/python -m pip check
```

On Linux/macOS replace `.venv/Scripts/python` with `.venv/bin/python`. Do not recreate an existing environment if it contains useful local work. The downloader alone needs Python 3.10+, standard library and Git for its rate-limit fallback; normalization reads R files without an R installation.

1. **Acquire/update originals**, when authorized source access is available: `python scripts/download_sources.py`. This accesses provider networks and changes source selections when newer files exist. Do not run it merely to reproduce the pinned local release. LRdb TLS failures and GtoPdb authentication require the documented verified manual-import route.
2. **Normalize verified local originals**: `python scripts/normalize_sources.py --report`. This is offline and retains source/species distinctions.
3. **Build accepted-policy views**: `python scripts/build_databases.py --repeat --skip-previews --annotation-dir "../gene-annotation-resources/annotations"`. This is offline but requires the three exact reference files pinned in [annotation-reference.json](config/annotation-reference.json). Another authorized location can be supplied. These assets are not part of this repository; a standalone clone is not yet a complete reproducible input bundle.
4. **Verify**: `python scripts/validate_normalization.py --repeat`, `python scripts/validate_database_release.py`, `python scripts/generate_field_guide.py --check`, and `python scripts/validate_documentation.py`. Use the environment's Python for every command.

`--skip-previews` avoids the optional Codex-provided Node/artifact runtime; full Excel writing and every-cell consistency validation still run. Without that flag, previews require that runtime. Individual commands and recovery procedures are in the script guide. No all-in-one acquisition/build command is provided.

## Read next

- [Database field guide](docs/Database%20dictionary.md): fields, actual examples, types, keys and safe joins.
- [Script guide](docs/Script%20guide.md): commands, dependencies, side effects and recovery.
- [Accepted database policies](docs/Accepted%20database%20policies.md): scientific inclusion decisions.
- [Final build report](docs/Final%20database%20build.md): generated counts and limitations.
- [Source acquisition](docs/Source%20acquisition.md) and [normalization usage](docs/Normalization%20usage.md).
- [Repository readiness](docs/Repository%20readiness.md): validation, cleanup, licensing and upload blockers.
- [Handoff index](docs/Handoff%20index.md): preserved milestone context.

## Licensing and publication status

This working tree is prepared for review, **not published or cleared for unrestricted upload**. The historical LICENSE file was empty; a project code license has not been selected. Provider software licenses do not license all underlying scientific data. Source citation/terms links are in [source_registry.py](scripts/source_registry.py) and acquisition metadata. Cite the contributing resources rather than treating this aggregation as experimental evidence.

ConnectomeDB's official download and policy pages conflict; OmniPath was obtained under academic access with heterogeneous upstream terms; GtoPdb specifies database/content licenses with access conditions. Historical Git data also need redistribution review. See the readiness report's explicit inclusion/withholding plan before staging files. Local `data/historical`, original sources and the Obsidian vault are preserved.
