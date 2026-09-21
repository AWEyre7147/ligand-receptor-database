# Initial assessment — 2026-09-20

> Scope update: the user chose current-source acquisition for both human and mouse, without species conversion. Version 1 downloads datasets and maintains one data/sources/versions.txt log. Historical reconstruction and annotation auditing below are superseded proposals. Supplied files now reside in data/historical. Follow [the current coding handoff](handoffs/001-download-current-sources.md).

This is a feasibility assessment and local input audit, not a completed ingestion pipeline. Official documentation and repositories were inspected. Download endpoints and parsers have not all been exercised end to end. Reference labels match the accompanying discussion.

## A05 — Feasibility and scope

Automated acquisition and rebuilding are feasible. Treat publication datasets as frozen inputs and evolving databases as versioned snapshots. A reproducible build must use pinned snapshots rather than whatever is live on the build date.

The existing repository already has Git history. At inspection, tracked README, PROJECT, AGENTS, LICENSE, CHANGELOG, environment, notebook and older output files were deleted in the working tree. These deletions were preserved. The two supplied reference files were untracked. No repository reset, commit, remote creation or pipeline implementation was performed.

## A06 — Reference workbook

`data/processed/Ligand_Receptor_DB.xlsx`, sheet `Ligand-Receptor`, contains 86,457 nonempty data rows and 86,457 distinct ordered endpoint pairs. Its columns are source (gene ID), target (gene ID), LR_pair, is_stimulation, is_inhibition, interaction, evidence, data source. Endpoint values are mostly symbols despite the ID labels.

73,236 master rows cite OmniPath. The OmniPathPPIs source tab is a broad protein-interaction input. The master therefore cannot be assumed to be a strictly extracellular ligand–receptor catalog. OmniPath provides a separate [intercellular-network workflow](https://workflows.omnipathdb.org/intercell-networks-py.html) that combines interactions with transmitter/receiver annotations.

The Home sheet reports 86,544 unique pairs, which disagrees with the actual master. Source-tab row counts are not uniformly pair counts. CellCall has 3,975 LR–TF/pathway rows but exactly 312 distinct symbol pairs. CellTalkDB has no header in its first row. Kirouac and ICELLNET have substantial empty formatted regions. These are requirements for the audit, not reasons to force a new output to the Home totals.

## A07 — Gene annotations

`gene annotation.txt` has 130,153 rows, 16 columns, 45,497 unique HGNC IDs and 45,497 unique approved-symbol values. There are no completely duplicated rows. Repeated HGNC records differ in annotation values; the first A1BG-AS1 records, for example, differ in previous symbol. This is consistent with expansion of multivalued HGNC-style annotations. Authorship, exact export tool and date are unknown.

The sibling annotations manifest reports 20,596 human protein-coding records and includes HGNC, Entrez, Ensembl, UniProt, aliases and functional annotations. It records run `20260920T002526867731Z`, schema `2.0.0`, and mode `cached-reexport`; the run date alone does not establish upstream retrieval freshness.

The human Excel annotation file exactly matches 8,928 of 9,147 distinct endpoint labels in the reference master (97.6%). The remaining 219 have not yet been fully resolved. Examples include legacy symbols (CTGF, CYR61, ATP5B), case anomalies (CCl19), labels requiring species review (CCL12, CD1D1), and noncoding/pseudogene labels. An exact-match miss is not proof of a missing gene. The sibling Parquet file was not read because the inspection runtime lacked a Parquet engine; Excel was used for this comparison.

Recommendation: reuse the existing annotation resource, audit aliases and stable IDs, and supplement only demonstrated gaps. It cannot provide interaction evidence, complex membership or source-specific ligand/receptor roles by itself.

## A08–A23 — Source registry assessment

| ID | Source | Acquisition and update recommendation | Important qualification |
|---|---|---|---|
| A08 | CellCall | [Author repository](https://github.com/ShellyCoder/cellcall): pin bundled LR–TF reference files to a commit; refresh on upstream data changes. | Choose core versus extended and human versus homology-derived resources explicitly. Deduplicate LR pairs while retaining TF/pathway provenance. |
| A09 | Cellinker (workbook: Celllinker) | [Downloads and API](https://www.rna-society.org/cellinker/Download.html): human/mouse text files and complex CSVs; bulk files preferred for reproducibility. | API documentation has inconsistent php_mysql/mysql_php paths. Alternate cellknowledge host timed out during review. Smoke-test the selected endpoint; no update cadence established. |
| A10 | OmniPathPPIs | [Python API](https://omnipath.readthedocs.io/en/latest/api.html) and HTTP service support automated retrieval. Pin query parameters and snapshot. | Broad PPIs are not all LR interactions. Apply intercellular roles for a strict LR view; retain original resource provenance. |
| A11 | Dimitrov | Likely [LIANA consensus](https://liana.readthedocs.io/en/stable/tutorials/notebooks/basic_usage.html): workbook resource column says consensus. Pin LIANA resource file/package version. | Exact historical version remains unconfirmed. This is an aggregate resource, not independent experimental corroboration. |
| A12 | CellPhoneDB (user: DellPhoneDB) | [Official data repository](https://github.com/ventolab/cellphonedb-data): versioned database archive or input CSV tables. | Join interaction, protein, gene and complex definitions. Preserve orientation and nonprotein ligand proxies. Workbook has 2,923 input rows, matching the documented v4.1 count, but that alone is not version proof. |
| A13 | Kirouac | Frozen publication resource: [2010 paper, PMID 20924352](https://pubmed.ncbi.nlm.nih.gov/20924352/). LIANA also exposes Kirouac2010. | Original supplementary retrieval was not verified; publisher fetch failed. Resolve original supplement against the workbook and retain an auditable static snapshot. A LIANA copy must be labeled as transformed. |
| A14 | CellChat | [Maintained author repository](https://github.com/jinworks/CellChat): species-specific CellChatDB R data objects, pinned to a commit/release. | Preserve complexes and cofactors. R-object extraction may require a small R conversion step. The web explorer does not include all v2 additions. |
| A15 | ConnectomeDB | [NATMI repository](https://github.com/forrest-lab/NATMI) for connectomeDB2020; [connectomeDB2025](https://connectomedb.org/docs/tutorials/) provides date-stamped bulk downloads. | Treat 2020 reproduction and updated 2025 ingestion as distinct versions. Newer curation can remove old pairs. Human web page is labeled 2026-03-16. |
| A16 | iTALK | [LR_database.rda](https://github.com/Coolgenome/iTALK/tree/master/data) bundled with the package. Pin and extract once; check for upstream changes. | Treat as a snapshot, not a guaranteed live service. Preserve interaction classification. |
| A17 | LRdb | [Official text distribution](https://github.com/SCA-IRCM/LRdb) includes LRdb_122019.txt. | Excellent historical source. Authors also describe separate updates in [BulkSignalR](https://github.com/jcolinge/BulkSignalR); confirm the intended newer LRdb distribution before assigning an automatic update policy. |
| A18 | Ramilowski | [FANTOM download](https://fantom.gsc.riken.jp/5/suppl/Ramilowski_et_al_2015/) provides PairsLigRec.txt, explicitly dated April 2015. | Frozen resource. Preserve the literature-supported versus putative distinction; do not relabel old data as newly curated. |
| A19 | Pavlicev | [2017 publication supplements](https://genome.cshlp.org/content/27/3/349/suppl/DC1) list Supplemental_Tables.xlsx. | Frozen resource. Download link was found but binary retrieval/table equivalence was not verified. Workbook source columns are Receptor then Ligand: reverse when normalizing. |
| A20 | NicheNet | [Author repository](https://github.com/saeyslab/nichenetr) and documented [Zenodo RDS downloads](https://github.com/saeyslab/nichenetr/blob/master/vignettes/differential_nichenet.md). | Import the LR network only, not ligand-target predictions or intracellular signaling edges. Pin model version and species. Aggregated provenance overlaps other sources. |
| A21 | GtoPdb | [Bulk CSV/TSV downloads](https://www.guidetopharmacology.org/download.jsp) and [REST API](https://www.guidetopharmacology.org/webServices.jsp). Versioned ongoing releases. | [Registration/API-key announcement](https://blog.guidetopharmacology.org/) places API-key rollout around September 15–17, 2026. Verify authenticated access. Restrict to appropriate species and endogenous gene-encoded ligands for a gene LR output; broad export contains synthetic compounds. Reference workbook records release 2023.1. |
| A22 | CellTalkDB | [Author repository](https://github.com/ZJUFanLab/CellTalkDB): database directory supplies human and mouse RDS resources. | Straightforward pinned download/conversion; treat v1.0 as a snapshot unless a newer data version is verified. |
| A23 | ICELLNET | [Official vignette](https://github.com/soumelis-lab/ICELLNET/blob/master/Vignette.md) documents direct data/ICELLNETdb.tsv download. | Straightforward TSV adapter; evolving database. Preserve all ligand/receptor subunits, family, references, and version. Current vignette describes 1,669 interactions, substantially beyond the old workbook. |

## A24 — Proposed build contract

Maintain a versioned source manifest: source ID, original URL, retrieval date, release/commit, species, checksum, original filename, citation, data terms, adapter version and upstream dependencies. Retain static inputs in the repository where redistribution permits. Access permission and redistribution permission are distinct. [OmniPath explicitly carries upstream licenses through](https://omnipathdb.org/); an aggregate cannot automatically be assigned one permissive license.

Use a canonical interaction table plus source evidence and complex membership tables internally. Preserve raw identifiers alongside normalized identifiers. Represent unknown stimulation/inhibition as missing, and conflicting evidence explicitly. Never infer inhibition merely from a zero stimulation flag. Keep source counts separate from counts of independent publications.

Generate sharing XLSX (primary sheet named Ligand-Receptor) and master Parquet from the same canonical records. Retain the reference's eight columns as a compatibility view while keeping enough internal metadata to represent species, complexes, provenance and unresolved mappings. Define how complex endpoints serialize before implementation. Avoid silently splitting an obligate heteromeric receptor into independent gene pairs.

Separate immutable historical reconstruction from updated curation. Exact historical reconstruction is not yet established because source versions, some transformations and supplementary matches remain unknown.

## A25 — Next handoff

See `handoffs/001-initialize-and-audit.md`. Initial implementation should establish the repository and baseline audit first. Biological inclusion policies should be decided before releasing a refreshed master.
