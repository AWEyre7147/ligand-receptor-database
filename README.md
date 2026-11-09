# Ligand–receptor databases

Human and mouse ligand–receptor databases assembled from 16 providers, with separate species identities and no species conversion.

| Output | Human | Mouse |
|---|---:|---:|
| Primary interactions | 12,091 | 9,585 |
| Nonprotein/proxy companion interactions | 1,999 | 998 |

## Use the data

Download the [human workbook](data/processed/Ligand-Receptor-Human-DB.xlsx) or [mouse workbook](data/processed/Ligand-Receptor-Mouse-DB.xlsx). Each contains five sheets: Ligand-Receptor, Nonprotein-Proxy, Entities, Complex-Members and Regulators. Required complex subunits and regulator relationships remain separate. Internal IDs identify records within a release.

For Python, use the Parquet files in `data/processed`. They retain typed lists, source assertions, evidence, review records and provenance omitted from Excel.

```python
import pandas as pd

interactions = pd.read_parquet('data/processed/Ligand-Receptor-Human-DB.parquet')
entities = pd.read_parquet('data/processed/Human-Entities.parquet')
```

The Excel files are readable input views. Multiple values use semicolons; use Parquet for exact list boundaries. Blank signs mean unreported, not inhibition. Provider-specific annotations retain their own meanings.

## Rebuild or update

Install Python 3.11+ and the dependencies in [requirements-normalization.txt](requirements-normalization.txt). Keep acquisition, normalization and final assembly separate:

```powershell
python scripts/download_sources.py
python scripts/normalize_sources.py
python scripts/build_databases.py --annotation-dir "../gene-annotation-resources/annotations"
```

Acquisition contacts providers and may replace source downloads. Some resources require manual downloads. Rebuilding existing inputs is offline and does not require acquisition. The build requires the exact separately supplied annotation files pinned in [config/annotation-reference.json](config/annotation-reference.json). The reference files are not bundled.

Routine builds perform integrity checks. `--release-verification` additionally runs the full suite, repeats assembly and compares the Excel projection exhaustively. It is a separate, more expensive operation.

## Documentation

- [Database dictionary](docs/Database%20dictionary.md): fields, identifiers and relationships.
- [Accepted database policies](docs/Accepted%20database%20policies.md): scientific inclusion and interpretation.
- [Script guide](docs/Script%20guide.md): supported commands, dependencies and verification.

Source citations and acquisition metadata are retained in `data/sources/versions.txt` and the source registry. Cite contributing resources when using the data. This is a computational integration resource, not independent experimental validation.
