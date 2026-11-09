# Database dictionary

This is the authoritative field guide for the current human and mouse databases. Its scientific descriptions live in `config/field-guide.json` and the two Markdown fragments beside it; [generate_field_guide.py](../scripts/generate_field_guide.py) verifies actual schemas and examples. Rebuild this guide explicitly after reviewing schema or vocabulary changes. The database builder never overwrites it.

Start with `Ligand-Receptor` in the [human workbook](../data/processed/Ligand-Receptor-Human-DB.xlsx) or [mouse workbook](../data/processed/Ligand-Receptor-Mouse-DB.xlsx). These contain 12,091 and 9,585 eligible interactions respectively. Use `Nonprotein-Proxy` alongside them (1,999 human and 998 mouse rows). The current companions contain **source-defined proxies**, not successful molecule-only coverage. Use Assertions and Evidence to evaluate support before making biological claims; use Review to study excluded or unresolved records. Shared Parquet audit tables retain records that cannot belong unambiguously to either species workbook.

## What a row means

- **Ligand-Receptor / Nonprotein-Proxy:** one ordered, species-local pair of canonical entities. An entity can be an intact complex or a mature peptide; a row is not necessarily a pair of single genes.
- **Assertions / Review:** one original source interaction record and its final disposition. Pathway repetitions remain separate assertions. Review is a filtered copy of Assertions, so never concatenate them to count evidence.
- **Evidence:** one typed source evidence claim attached to one assertion. Database membership, pathway and free text are not direct publication proof. No citations were fetched or independently verified during assembly.
- **Source-Annotations:** one original provider field/value attached to its supplying source record. `summary_eligible=false` values remain traceable but do not populate interaction summaries. Use this table to recover which GtoPdb action, comment, selectivity and endogenous values actually co-occurred on a measurement record.
- **Entities:** one species-local canonical identity. A proxy is not its product; an encoded peptide retains its molecular ID and an `encoded_by` link to its precursor gene.
- **Complex-Members:** one canonical dependency edge. `required_subunit` members act together; `encoded_by` and biosynthetic/transport dependencies have different meanings. Unknown stoichiometry is not one.
- **Complex-Definitions:** one resolved source definition; several definitions can map to one canonical entity. Incompatible complete member sets, stoichiometry or assembly context keep separate identities.
- **Source-Members:** one unchanged normalized source membership claim plus final definition/entity links where resolved. Original GtoPdb subunit lists can describe alternative families: preservation here does not endorse an obligate complex.
- **Regulators:** one CellChat optional regulator member per original interaction/group. Agonists, antagonists and coreceptors are not silently appended to required subunits.
- **Sources (Parquet):** one provider's acquisition selection, citation and normalized record count. Each species' Sources Parquet contains all 16 providers; this technical table is omitted from Excel.
- **Readme:** one interpretation topic, not biological data.

The accepted [policies](Accepted%20database%20policies.md) control inclusion. Provider-derived mouse orthology evidence is labeled inferred, and unknown provenance remains unknown. No species conversion, case-based gene conversion or new orthology mapping is performed. Source counts and publication counts are overlap-aware summaries, **not independent-replication scores**. A source's `native_reported` label is not independent verification of a native experiment.

## Keys and joins

Final navigation IDs use readable prefixes and at least six digits: LRI, ENT, MEM, REG, CDF, ANN, AST, EVD and SCX. They are numbered across all species before partitioning and are local to a release. Use the ID together with its build manifest; a later release may renumber it. Normalized record/evidence keys and source-complex keys remain unchanged in Parquet for provenance. Provider accessions are separate from these internal IDs. Do not use display labels or row numbers as cross-source keys.

| From | To | Cardinality and interpretation |
|---|---|---|
| interaction `interaction_id` | Assertions `interaction_id` | 1:many eligible assertions; only primary/companion rows support it |
| assertion `record_key` | normalized records `record_key` | 1:1 across all sources; exposes complete original `raw_json` |
| assertion `record_key` | Evidence / Regulators / Source-Annotations `record_key` | 1:zero-or-many; absent evidence or annotation is not fabricated |
| interaction `interaction_id` | Source-Annotations `interaction_id` | 1:zero-or-many eligible supplying records; source-prefixed interaction columns are independent sorted-distinct summaries of these rows |
| interaction/assertion endpoint entity IDs | Entities `entity_id` | many:1; unresolved assertion endpoints can be null |
| Complex-Members `entity_id`, `member_entity_id` | Entities `entity_id` | many:1 at each end; parent:member is many:many overall |
| Complex-Definitions `entity_id` | Entities `entity_id` | many:1 |
| Source-Members (`source`, `complex_key`) | Complex-Definitions (`source`, `source_complex_key`) | many:zero-or-one; unresolved definitions have null final links |
| Complex-Definitions `supporting_definition_ids` | Complex-Definitions `definition_id` | list-valued structural support; explode explicitly if needed |
| any `source` | Sources `source` | many:1 within one workbook; do not concatenate duplicated Sources sheets |
| review assertion `related_interaction_id` | interaction `interaction_id` | optional many:1 navigation only, never support |

Evidence and annotation values can repeat across assertions and sources. Join Assertions to interaction views before Evidence when counting source support; joining one-to-many tables first can multiply rows. Summary fields are aggregated independently and do not imply that values in different columns came from the same provider record; use Source-Annotations and `record_key` for that question. Neither Review nor companion views should be concatenated into primary counts without preserving their meaning.

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

Excel follows the approved five-sheet templates. Lists display as semicolon-separated text and empty lists are blank. This display is not a reversible list encoding: original values can themselves contain semicolons, so use Parquet when exact value boundaries matter. Literal text, including formula-leading characters, stays text. Do not coerce identifiers to numbers. Missing sign summaries are blank, while an eligible provider's explicit unknown can remain `unknown`. The exporter refuses cells exceeding Excel's 32,767-character limit rather than truncating them. Evidence, assertions, review, source annotations and technical metadata remain complete in Parquet.
