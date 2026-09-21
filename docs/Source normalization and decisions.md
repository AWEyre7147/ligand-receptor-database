# Source normalization and decisions

| Source | Retained raw records | Distinct semantic assertions | Human / mouse nonexcluded assertions | Unresolved records | Parsing / scope limitation |
|---|---:|---:|---:|---:|---|
| cellcall | 38,645 | 2,388 | 1,448 / 940 | 0 | LR–TF/pathway rows; core and extended retained. |
| cellinker | 6,985 | 6,985 | 3,744 / 3,241 | 0 | Complex IDs joined; native/inferred mouse evidence unknown. |
| omnipathppis | 11,092 | 11,092 | 6,658 / 4,434 | 0 | PPI orientation unresolved for some human and all mouse rows. |
| dimitrov | 35,356 | 8,112 | 8,112 / 0 | 0 | Consensus plus constituent memberships; not independent corroboration. |
| cellphonedb | 2,911 | 2,911 | 2,911 / 0 | 0 | Non-LR pair classes and enzyme proxies retained for review. |
| kirouac | 637 | 636 | 636 / 0 | 232 | 405 numeric mapping rows plus 232 unresolved S12 text assertions. |
| cellchat | 6,612 | 6,612 | 3,233 / 3,379 | 0 | Nested R tables read; cofactors separate; nonprotein proxies typed. |
| connectomedb | 6,802 | 6,778 | 3,550 / 3,228 | 1 | One ambiguous mouse receptor ID list; AI links are not experimental evidence. |
| italk | 2,649 | 2,592 | 2,575 / 0 | 17 | 17 missing approved receptor symbols retained with source names and unknown partner species. |
| lrdb | 3,639 | 3,639 | 3,639 / 0 | 0 | Manual import usable; no pair-level references. |
| ramilowski | 2,557 | 2,557 | 2,557 / 0 | 0 | Putative rows and possible enzyme proxies remain review records. |
| pavlicev | 1,006 | 1,001 | 1,001 / 0 | 0 | S5 only; reversed header order; exact proxy count not annotated. |
| nichenet | 10,654 | 10,600 | 4,986 / 5,614 | 0 | Aggregate membership only; mouse orthology-derived. |
| gtopdb | 24,934 | 22,768 | 498 / 16 | 3,373 | Pharmacology assays, unknown/mixed/cross species and explicit exclusions retained. |
| celltalkdb | 5,431 | 5,431 | 3,398 / 2,033 | 0 | Same-species source IDs used; mouse evidence provenance unknown. |
| icellnet | 1,669 | 1,669 | 1,669 / 0 | 0 | Required ligand/receptor subunits preserved together. |

**16/16 sources normalized; 161,579 interaction records retained.** Raw interaction counts reconcile one-to-one with normalized records: no interaction expansion, aggregation or row dropping. Repeated assays, LR–TF rows and evidence-membership rows remain separate. Supporting table counts/schemas, source checksums, releases and outputs are in `data/interim/manifest.json`.

“Distinct semantic assertions” means a within-source key containing typed endpoint IDs, both species sets, complex identity and orientation. It is not a count of independently validated LR pairs. Unresolved Kirouac text assertions and pharmacology records are included in that column. Human/mouse counts require both endpoints to have the same single species and exclude explicit out-of-scope rows, but include records awaiting decisions. They are **candidate pools**, not approved masters. Counts across sources must not be added as unique pairs.

An unresolved record has an absent or ambiguous necessary identifier. Untouched source symbols are separately labeled `source_symbol_unverified`; they have not been certified against modern gene nomenclature. Original whitespace/case and all source interaction fields remain in `raw_json`, with original endpoint labels retained separately. No sibling annotation resource or species translation was used.

## N01 — Provider-derived mouse orthology

**Recommendation:** retain provider-derived mouse interactions as a separately labeled inferred tier, with provenance and original source membership exposed in both future formats. Offer a native-evidence-only view only after record-level native support is established. Do not relabel the unknown-provenance tier as native.

| Source | Mouse records | Known provider orthology | Unknown native/inferred provenance | Distinct mouse assertions |
|---|---:|---:|---:|---:|
| cellcall | 15,526 | 15,526 | 0 | 940 |
| cellinker | 3,241 | 0 | 3,241 | 3,241 |
| omnipathppis | 4,434 | 4,434 | 0 | 4,434 |
| cellchat | 3,379 | 0 | 3,379 | 3,379 |
| connectomedb | 3,252 | 3,252 | 0 | 3,228 |
| nichenet | 5,668 | 5,668 | 0 | 5,614 |
| gtopdb | 21 | 0 | 21 | 18 |
| celltalkdb | 2,033 | 0 | 2,033 | 2,033 |

Across per-source rows, **28,880 known inferred mouse records** and **8,674 unknown-provenance mouse records** are distinguishable. These are overlapping source records, not a cross-source union. No mouse record is asserted here to have verified native experimental support. Human asset provenance labeled “native” is also not promoted automatically to pair-level experimental proof.

Examples: CellCall homology LR–TF rows, ConnectomeDB `A2m → Lrp1` and the NicheNet mouse network keep the provider-orthology label. CellChat `Tgfb1 → TGFbR1_R2`, Cellinker mouse interactions and CellTalkDB mouse pairs remain unknown-provenance. ConnectomeDB mouse `Evidence=Direct` is retained verbatim but does not override the supplied dataset-level orthology provenance. GtoPdb `CCL19 → CCR7` with explicit Mouse/Mouse fields is species-compatible; provenance of native experimental support still requires evidence review.

**Decision requested:** include inferred evidence as a labeled tier, or require a native-only final mouse scope (which needs additional provenance review rather than treating all unflagged rows as native).

## N02 — Multi-subunit complexes

**Recommendation:** one interaction connects complete endpoint entities. Keep required members in `memberships.parquet`; keep CellChat agonists, antagonists and activating/inhibitory co-receptors in `regulators.parquet`. Do not generate a Cartesian product of ligand and receptor subunits. Unknown alternatives remain unexpanded text.

| Source | Records involving a declared complex | Records with ≥2 required members | Distinct assertions with ≥2 required members |
|---|---:|---:|---:|
| cellcall | 2,014 | 2,014 | 340 |
| cellinker | 912 | 912 | 912 |
| omnipathppis | 2,051 | 1,910 | 1,910 |
| dimitrov | 4,449 | 4,449 | 1,240 |
| cellphonedb | 1,345 | 1,338 | 1,338 |
| cellchat | 2,831 | 2,831 | 2,831 |
| gtopdb | 483 | 412 | 385 |
| icellnet | 668 | 668 | 668 |

These counts exclude biosynthetic/transport proxy components from the required-protein-subunit count. A declared complex can contain one listed gene (for example a homomer with unprovided stoichiometry), so the two columns differ. Source-supplied stoichiometry stays available at the cited raw definition; missing stoichiometry is not invented.

For example, a later Excel row could display `IL12A + IL12B → IL12RB1 + IL12RB2` with separate endpoint complex IDs and a membership sheet. Parquet would keep those same IDs plus four required-member rows; this is **one** interaction, not four. CellChat `TGFB1 → TGFbR1_R2` keeps `TGFBR1` and `TGFBR2` required while its antagonists remain regulator links. CellCall receptor commas are split only because its source implementation explicitly treats them as required complexes. NicheNet `C4B_2` remains one literal label. Kirouac S12 `ADIPOR 1/2` remains an unresolved alternative/complex assertion.

**Decision requested:** preserve complex endpoints in the masters as recommended; decide separately how unresolved alternatives and incomplete complex definitions should appear. No subunit splitting has been performed in these intermediates.

## N03 — Nonprotein ligands and enzyme proxies

**Recommendation:** retain a gene-encoded LR view and a separate typed nonprotein/proxy view. A biosynthetic enzyme is a proxy for production, not the ligand molecule. If the expanded scope is selected later, keep molecule identifiers, proxy identifiers, dependency roles and measured species separate.

| Source | Flagged nonprotein/proxy records | Distinct flagged assertions | Qualification |
|---|---:|---:|---|
| cellphonedb | 1,029 | 1,029 | Explicit source proxy/nonprotein semantics. |
| cellchat | 1,996 | 1,996 | Explicit source proxy/nonprotein semantics. |
| italk | 15 | 15 | Potential enzyme proxies based on ligand description; not a confirmed proxy count. |
| lrdb | 15 | 15 | Potential enzyme proxies based on ligand description; not a confirmed proxy count. |
| ramilowski | 15 | 15 | Potential enzyme proxies based on ligand description; not a confirmed proxy count. |
| gtopdb | 2,284 | 2,098 | Includes retained pharmacological exclusions; use status before inclusion. |

CellPhoneDB `Acetylcholine_byCHAT → CHRM1` remains a proxy entity whose component is CHAT; neither CHAT nor its UniProt accession is renamed acetylcholine. CellChat uses `annotation=Non-protein Signaling`, not `is_neurotransmitter`: that flag also marks protein pathways such as WNT. Four CellPhoneDB hCGB complex interactions have `is_ppi=False` despite protein-complex definitions; those conflicts are flagged rather than counted automatically as nonprotein ligands.

Pavlicev S5 explicitly includes receptor–biosynthetic-enzyme associations but provides no per-row proxy flag. All 1,006 S5 records therefore retain a proxy-classification review flag, and the exact count of true proxies is **undetermined**. Examples `HSD3B1 → PAQR7` and `HSD17B2 → ESR1` remain original gene proxies/labels for review; no metabolite identity is invented. Labels such as `CCl19`, `FGF12B` and `SCYA*` remain unchanged.

GtoPdb release **2026.3** contains **24,934 assay/interaction rows**, including **1,682 Endogenous=true** and **875 endogenous peptide rows** before species and entity review. Explicit pharmacological/out-of-scope exclusions retain **22,244 rows** with reasons. Endogenous status and ligand type are distinct tests; metabolites can be endogenous.

| GtoPdb normalized endpoint species class | Records |
|---|---:|
| cross_species | 180 |
| human | 604 |
| mixed_species | 349 |
| mouse | 21 |
| other_species | 28 |
| unknown_species | 23,752 |

The missing ligand species on pharmacological molecules is not filled from target species. Multi-species peptide labels remain sets and are not expanded into species-specific pairs. Peptide subunit and target-subunit IDs use their respective GtoPdb namespaces. The local peptide table does not provide full small-molecule metadata; some target-as-ligand entities remain unresolved. Raw Action/Type values and repeated affinity measurements survive; agonism/binding is not converted into a universal activation sign.

**Decision requested:** gene-encoded LR scope only, or include a separately typed nonprotein/proxy tier. Precise classification of Pavlicev proxies and missing small-molecule companion metadata remain follow-up work under either policy.

## N04 — Additional decisions and evidence overlap

- **Interaction scope/direction:** keep CellPhoneDB adhesion, gap-junction, ligand–ligand and receptor–receptor rows as a separate class or exclude them from the strict LR view. OmniPath source→target is a signaling edge, not always ligand→receptor. Unique human ligand/receptor-role matches are oriented; ambiguous and mouse edges stay unresolved. Unknown signs remain null, and conflicting positive signs are flagged. Reversing endpoints never transfers the original PPI sign to the reverse relation.
- **Aggregate evidence:** use LIANA `resource=consensus` as the Dimitrov resource while preserving its constituent rows for provenance. OmniPath, LIANA, NicheNet and several curated databases overlap; database membership and repeated citations must not count as independent biological replication. LRdb and iTALK lack pair-level references; neither database citation is assigned to all rows. ConnectomeDB PubMed IDs embedded in provider summary links have a distinct evidence type.
- **Species/identifier uncertainty:** decide whether mixed-species, cross-species, unspecified species, Kirouac free-text receptor alternatives, Ramilowski putative pairs and unresolved legacy symbols should be excluded from the strict view or retained in explicit review tiers. iTALK missing approved receptor symbols retain their names (including ECRF3 and US28) with unknown partner species; the human dataset label does not settle those endpoint species.

## Reconciliation, validation and use

Run `python scripts/normalize_sources.py --report` after installing `requirements-normalization.txt`; use `--source <id>` for a focused rebuild. See [Normalization usage](Normalization%20usage.md) for schema, provenance, failure behavior and tests. Each source has typed `records.parquet`, `evidence.parquet`, `memberships.parquet`, `regulators.parquet` and `review_examples.tsv`. Review extracts are samples, not a filtered replacement for the full intermediates.

The command verifies all used raw input checksums before and after, verifies row reconciliation and unique record keys, validates typed Parquet roundtrips and resolves evidence/regulator and complex-membership references. Full-build repeat determinism and raw/vault preservation are recorded in `data/interim/validation.json` by the validation command. Per-source parse limitations are retained in the manifest. R tibble class notices mean conversion to data frames; all table counts, columns and row identities are retained. No R package source code is executed.

All current local sources parse. LRdb/GtoPdb online acquisition blockers do not block these offline imports. The original files, `versions.txt`, historical data and existing Obsidian notes/settings remain unchanged. **Final human/mouse master XLSX and Parquet generation is deferred until N01–N03 and the substantive N04 scope decisions are resolved.**

Source-semantics references: [CellCall required receptor complexes](https://github.com/ShellyCoder/cellcall/blob/master/R/data2ConnectProfile.R), [CellChat database structure](https://github.com/jinworks/CellChat), plus the local CellPhoneDB complex/protein tables, GtoPdb release headers and Pavlicev S5 preamble. Acquisition citations/terms remain in the unmodified source manifest; they are dataset provenance, not pair evidence.
