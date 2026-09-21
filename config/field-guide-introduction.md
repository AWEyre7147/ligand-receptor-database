# Database dictionary

This is the authoritative field guide for the current human and mouse databases. Its scientific descriptions live in `config/field-guide.json` and the two Markdown fragments beside it; [generate_field_guide.py](../scripts/generate_field_guide.py) verifies actual schemas and examples. Rebuild this guide explicitly after reviewing schema or vocabulary changes. The database builder never overwrites it.

Start with `Ligand-Receptor` in the [human workbook](../data/processed/Ligand-Receptor-Human-DB.xlsx) or [mouse workbook](../data/processed/Ligand-Receptor-Mouse-DB.xlsx). These contain 12,091 and 9,585 eligible interactions respectively. Use `Nonprotein-Proxy` alongside them (1,999 human and 998 mouse rows). The current companions contain **source-defined proxies**, not successful molecule-only coverage. Use Assertions and Evidence to evaluate support before making biological claims; use Review to study excluded or unresolved records. Shared Parquet audit tables retain records that cannot belong unambiguously to either species workbook.

## What a row means

- **Ligand-Receptor / Nonprotein-Proxy:** one ordered, species-local pair of canonical entities. An entity can be an intact complex or a mature peptide; a row is not necessarily a pair of single genes.
- **Assertions / Review:** one original source interaction record and its final disposition. Pathway repetitions remain separate assertions. Review is a filtered copy of Assertions, so never concatenate them to count evidence.
- **Evidence:** one typed source evidence claim attached to one assertion. Database membership, pathway and free text are not direct publication proof. No citations were fetched or independently verified during assembly.
- **Entities:** one species-local canonical identity. A proxy is not its product; an encoded peptide retains its molecular ID and an `encoded_by` link to its precursor gene.
- **Complex-Members:** one canonical dependency edge. `required_subunit` members act together; `encoded_by` and biosynthetic/transport dependencies have different meanings. Unknown stoichiometry is not one.
- **Complex-Definitions:** one resolved source definition; several definitions can map to one canonical entity. Incompatible complete member sets, stoichiometry or assembly context keep separate identities.
- **Source-Members:** one unchanged normalized source membership claim plus final definition/entity links where resolved. Original GtoPdb subunit lists can describe alternative families: preservation here does not endorse an obligate complex.
- **Regulators:** one CellChat optional regulator member per original interaction/group. Agonists, antagonists and coreceptors are not silently appended to required subunits.
- **Sources:** one provider's acquisition selection, citation and normalized record count. Both workbooks contain all 16 providers for transparency, even when a provider contributes no eligible interaction of that species.
- **Readme:** one interpretation topic, not biological data.

The accepted [policies](Accepted%20database%20policies.md) control inclusion. Provider-derived mouse orthology evidence is labeled inferred, and unknown provenance remains unknown. No species conversion, case-based gene conversion or new orthology mapping is performed. Source counts and publication counts are overlap-aware summaries, **not independent-replication scores**. A source's `native_reported` label is not independent verification of a native experiment.

## Keys and joins

Keys are deterministic text, with 32 hexadecimal characters from SHA-256 of compact ordered JSON; interaction/entity/definition/regulator keys add I:/E:/D:/R: prefixes; membership, record and evidence keys remain unprefixed. They are stable only while identity inputs, source row locations/order, schema and policy remain stable. Source version changes can change record keys without changing biology. Do not use display labels or row numbers as cross-source keys.

| From | To | Cardinality and interpretation |
|---|---|---|
| interaction `interaction_id` | Assertions `interaction_id` | 1:many eligible assertions; only primary/companion rows support it |
| assertion `record_key` | normalized records `record_key` | 1:1 across all sources; exposes complete original `raw_json` |
| assertion `record_key` | Evidence / Regulators `record_key` | 1:zero-or-many; absent evidence is not fabricated |
| interaction/assertion endpoint entity IDs | Entities `entity_id` | many:1; unresolved assertion endpoints can be null |
| Complex-Members `entity_id`, `member_entity_id` | Entities `entity_id` | many:1 at each end; parent:member is many:many overall |
| Complex-Definitions `entity_id` | Entities `entity_id` | many:1 |
| Source-Members (`source`, `complex_key`) | Complex-Definitions (`source`, `source_complex_key`) | many:zero-or-one; unresolved definitions have null final links |
| Complex-Definitions `supporting_definition_ids` | Complex-Definitions `definition_id` | list-valued structural support; explode explicitly if needed |
| any `source` | Sources `source` | many:1 within one workbook; do not concatenate duplicated Sources sheets |
| review assertion `related_interaction_id` | interaction `interaction_id` | optional many:1 navigation only, never support |

Evidence values can repeat across assertions and sources. Join Assertions to interaction views before Evidence when counting source support; joining both one-to-many tables first can multiply rows. Neither Review nor companion views should be concatenated into primary counts without preserving their meaning.

## Safe loading example

Run from the repository root with the declared Python dependencies installed. Parquet is preferable for analysis because it preserves types directly.

```python
from pathlib import Path
import pyarrow.parquet as pq

root = Path('data/processed')
pairs = pq.read_table(root / 'Ligand-Receptor-Human-DB.parquet').to_pandas()
assertions = pq.read_table(root / 'Human-Assertions.parquet').to_pandas()
evidence = pq.read_table(root / 'Human-Evidence.parquet').to_pandas()
support = assertions[assertions['disposition'].isin(['primary', 'companion'])]
primary_support = support.merge(pairs[['interaction_id']], on='interaction_id', validate='many_to_one')
claims = evidence.merge(primary_support[['record_key']], on='record_key', validate='many_to_one')
# Count unique evidence values by type; row count is not independent replication.
direct_pmids = claims.loc[claims['type'].eq('pubmed'), 'value'].drop_duplicates()
```

For Excel, use a cell-aware reader such as openpyxl with `data_only=False`; decode list columns with `json.loads`. For scalar text beginning `~json:`, apply `json.loads(value[6:])`. Do not strip the envelope without JSON decoding or coerce identifier strings to numbers. Blank scalar cells represent null. The `~json:` envelope also preserves an original empty string or literal prefix. The exporter refuses cells exceeding Excel's 32,767-character limit rather than truncating them.
