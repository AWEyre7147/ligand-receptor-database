# Codex handoff 001 — Download current ligand–receptor sources

Status: ready for implementation; this handoff has not been executed. Supersedes the earlier historical reconstruction and annotation-audit proposal.

## Objective and scope

Implement and run a simple, primarily Python downloader for the 16 sources below. On each run, identify their latest available relevant datasets, download new or changed files, and maintain one central version log. Acquire source-provided human and mouse data without converting interactions between species.

Version 1 is acquisition only. Do not generate master tables, reproduce or audit the historical workbook, investigate annotation gaps, build annotations, or add scheduled workflows. Later stages will produce Ligand-Receptor-Human-DB and Ligand-Receptor-Mouse-DB in XLSX and Parquet.

## Workspace

Root: `C:/Users/aweyr/OneDrive/Documents/Cheng-Lab/Tool-Development/ligand-receptor-database`.

```text
data/
  historical/                  # Existing supplied files; leave unchanged
  sources/
    cellcall/
    cellinker/
    omnipathppis/
    dimitrov/
    cellphonedb/
    kirouac/
    cellchat/
    connectomedb/
    italk/
    lrdb/
    ramilowski/
    pavlicev/
    nichenet/
    gtopdb/
    celltalkdb/
    icellnet/
    versions.txt               # Single authoritative acquisition log
docs/                          # Existing Obsidian vault
```

Use canonical source names. Document Celllinker as an alias of Cellinker and DellPhoneDB as an alias of CellPhoneDB. Preserve original filenames where practical, using species subfolders if needed to avoid collisions. Do not duplicate shared files unnecessarily.

Read applicable instructions and inspect Git status before editing. Existing working-tree deletions are user changes: do not reset or restore the old project. Leave data/historical byte-for-byte unchanged, and preserve existing vault notes and docs/.obsidian. No remote creation, push or publishing is requested.

## Implementation

Use a small Python package or script, minimal dependencies, and one documented command to update all sources. Provide a single-source option for retries if useful. Avoid workflow frameworks, databases, dashboards, snapshot archives and unnecessary configuration layers. Keep source definitions in one code/config location.

Prefer official bulk downloads or data-only repository files over installing full analysis packages. Resolve the latest official data release at runtime, or the current official data commit when no release exists. Record what was selected. Publication-only datasets may remain static indefinitely. Never infer versions from historical pair counts or use the historical workbook as a silent fallback.

Download supporting gene/protein lookup, complex and evidence tables needed to interpret the interactions. Avoid expression datasets, examples, ligand-target matrices and unrelated intracellular networks. Raw RDA/RDS assets can remain in their original format; defer conversion unless needed for validation. Preserve raw content; normalization, biological filtering and merging belong to later stages.

For OmniPath, acquire the interactions and intercellular annotations necessary for the agreed ligand–receptor scope, recording query parameters. Do not describe broad PPIs as a finished LR database.

### Species policy

Acquire human and mouse datasets wherever supplied. Record human-only, mouse-only, shared or unknown coverage explicitly. Never manufacture a missing species dataset through orthology mapping, capitalization changes or a client's automatic species translation.

If a provider's mouse resource is already derived through orthology, record that provenance explicitly. It may be retained as a labeled raw asset for later inclusion review, but must not be described as native mouse experimental evidence. Do not perform new conversions. A source lacking mouse data is a coverage limitation, not a reason to invent it.

### One central version log

Store UTF-8, indented JSON in data/sources/versions.txt. It is readable text and can be parsed with Python's standard library. Include a schema version and one source entry with its file records. Do not add separate per-source version logs.

Record source/provider name, release/version/commit when available, citation and terms URL, and for each file: relative path, download URL, species, relevant native/orthology-derived/unknown provenance, file size and SHA-256. Retain ETag/Last-Modified when useful. Record UTC last successful check/download times separately from latest attempt time, status and error. Include a concise per-run content-change result.

Check upstream release/commit metadata or reliable HTTP validators. If reliable indicators are absent, download and compare checksums. A newer check date alone is not a data change. Verify local files exist and match recorded checksums before accepting a not-modified response. Fetch into temporary files, validate, then replace previous good files. Write versions.txt atomically. Failed attempts must preserve previous valid data and successful metadata, while recording the error. For related files, promote the set only after required files validate so a partial update is not marked complete.

Keep the log focused on acquisition. Do not implement a generalized downstream rebuild system now. Later master-table generation can compare these checksums against its own last successful inputs; per-run changed flags alone are insufficient if a build was skipped or failed.

### Failures and validation

Use bounded timeouts/retries, normal TLS verification and explicit HTTP error handling. Detect login/error HTML in place of data. Validate nonempty payloads and format signatures or headers as appropriate, not just HTTP success. Use environment variables for credentials if necessary; never log or commit secrets.

Continue unaffected sources after a failure. Print updated, unchanged, unavailable/authentication-required and failed summaries. Return an unsuccessful exit status for incomplete required acquisition. Do not report partial success as a complete 16-source download. Do not silently substitute aggregators for originals; identify any processed distribution and its true provider explicitly.

## Sources to investigate and acquire

These are discovery starting points, not fixed current versions. Verify current official paths and assets during coding. The earlier initial-assessment.md is research context only; its historical, human-only and annotation-audit proposals are superseded.

| Source | Starting point and note |
|---|---|
| CellCall | https://github.com/ShellyCoder/cellcall — LR–TF reference assets; preserve core/extended and species distinctions. |
| Cellinker | https://www.rna-society.org/cellinker/Download.html — interaction and complex files; verify current host and endpoint paths. |
| OmniPathPPIs | https://omnipath.readthedocs.io/en/latest/api.html — interaction service plus intercellular roles; avoid automatic species translation. |
| Dimitrov | https://liana.readthedocs.io/ — current LIANA consensus resource; identify it as an aggregate and record its actual version. |
| CellPhoneDB | https://github.com/ventolab/cellphonedb-data — current inputs/archive and entity/complex definitions. |
| Kirouac | https://pubmed.ncbi.nlm.nih.gov/20924352/ — static supplementary data. LIANA's processed resource is a possible explicitly identified alternative if necessary. |
| CellChat | https://github.com/jinworks/CellChat — species-specific database objects with complex/cofactor information. |
| ConnectomeDB | https://connectomedb.org/ — current date-stamped bulk datasets; do not select an old release to match the workbook. |
| iTALK | https://github.com/Coolgenome/iTALK — bundled data/LR_database.rda. |
| LRdb | https://github.com/SCA-IRCM/LRdb and https://github.com/jcolinge/BulkSignalR — follow official references to establish the current LRdb distribution. |
| Ramilowski | https://fantom.gsc.riken.jp/5/suppl/Ramilowski_et_al_2015/ — static PairsLigRec.txt. |
| Pavlicev | https://genome.cshlp.org/content/27/3/349/suppl/DC1 — retrieve the publication's supplementary tables. |
| NicheNet | https://github.com/saeyslab/nichenetr — current documented LR-network downloads, not ligand-target matrices. |
| GtoPdb | https://www.guidetopharmacology.org/download.jsp and https://www.guidetopharmacology.org/webServices.jsp — verify current authentication requirements. |
| CellTalkDB | https://github.com/ZJUFanLab/CellTalkDB — human/mouse database files and required supporting metadata. |
| ICELLNET | https://github.com/soumelis-lab/ICELLNET — current data/ICELLNETdb.tsv and necessary supporting assets. |

Retain downloaded datasets under data/sources, with attribution and recorded redistribution terms. Keep third-party data terms separate from software licensing. Flag known redistribution limitations before a later public push. Ignore temporary files and secrets, not the intended source data or version log.

## Verification and deliverables

Test substantive cases: unchanged data, changed content without version metadata, missing/corrupt local files, invalid payloads and failed updates preserving previous good files. Verify species metadata and that no conversions are invoked. Run against all 16 sources and run again to check update detection, distinguishing actual upstream changes from defects.

Deliver the working downloader, minimal setup/dependency files, successfully acquired relevant assets, versions.txt, and a concise Obsidian-compatible note in docs explaining the command, layout, update behavior and limitations. Report actual source successes/failures, human/mouse coverage, tests run and credential/endpoint blockers. Preserve historical files. Do not claim the later XLSX/Parquet outputs are implemented.
