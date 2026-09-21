# Source acquisition — version 1

Implements [handoffs/001-download-current-sources](handoffs/001-download-current-sources.md). This stage downloads original source assets and detects updates. It does not normalize, merge, build annotations, translate species, create master XLSX/Parquet tables, or schedule runs.

## Run

Requires Python 3.10+ with normal TLS trust. No pip packages are required. Git on PATH enables the fallback when GitHub's anonymous API quota is exhausted; alternatively supply `GITHUB_TOKEN` as an environment variable. Never put tokens in URLs or files.

From the repository root:

```sh
python scripts/download_sources.py
```

Retry a source with `python scripts/download_sources.py --source lrdb` (repeat `--source` to select several). Test with `python -m unittest discover -s tests -v`.

Python was not on PATH during initial acquisition, so that milestone used the host-bundled interpreter. For portable setup, install Python 3.11+ and follow the [Script guide](Script%20guide.md); the downloader alone supports Python 3.10+. Output paths resolve from the script location, not the shell current directory.

## Layout and update behavior

- `scripts/source_registry.py`: all 16 source definitions, citations, terms, discovery rules and species provenance.
- `data/sources/<source>/`: current raw files, with original names and species subfolders where needed. R objects remain R objects. Europe PMC ZIP members are extracted byte-for-byte; unrelated supplementary figures are discarded.
- `data/sources/versions.txt`: the single authoritative UTF-8 JSON acquisition log. Includes selected releases/commits, file URLs, archive member names, species, provenance, size, SHA-256, useful HTTP validators, successful check/download timestamps, latest attempt/error, and the last run summary.

Each run resolves release/commit metadata or provider download catalogs. CellPhoneDB uses its latest data release; LIANA and CellTalkDB use their latest bundled release. CellChat and ICELLNET use the current officially documented data commit because software tags can lag data updates. Sources without releases use current commits. NicheNet follows the documented Zenodo model and its latest-version link. Static publication datasets remain publication-versioned; access dates are never treated as data versions.

GitHub API rate limiting triggers an official `git ls-remote` fallback, resolving the same release/commit without cloning. That fallback checks the known required paths; newly added support-file paths require a registry review. If Git is unavailable, the source reports an incomplete check rather than assuming cached data are current.

Local SHA-256 is verified before trusting immutable upstream metadata or HTTP 304. Without dependable validators the file is downloaded and compared. Changed metadata alone is not changed data. Missing/corrupt local files are repaired and logged separately from upstream content changes. Unchanged files retain their modification times. Binary signatures, ZIP CRCs, R compression/serialization signatures, nonempty table bodies and applicable headers are checked; this is acquisition validation, not a biological audit or full R-object conversion.

Required files are staged and validated as a set before promotion. Ordinary failures preserve the previous set and successful metadata. The log is replaced atomically after promotion. A process crash can leave a temporary backup: the next run compares current and backup files against the committed manifest and recovers only a matching complete set. Unresolvable recovery stops for inspection. If a terminated process leaves `.download.lock`, first confirm no downloader is running, then remove that lock and rerun. Temporary staging/backup files are ignored; intended data and the log are not ignored.

HTTP requests use 45-second socket timeouts, at most three attempts for transient failures, normal certificate verification and a 150 MB payload ceiling. Git fallback has a 60-second timeout. Unaffected sources continue after a failure. Exit code **1** means at least one requested source is incomplete; a single-source successful retry returns 0. `content_change=not_checked` after a failure does not erase the checksums of earlier successful files. Future builders should compare checksums against their own successful inputs.

## Verified availability — 2026-09-20

### Subsequent manual GtoPdb import

All three user-provided CSVs were structurally validated and copied byte-for-byte to data/sources/gtopdb. Each embeds the same release: **2026.3, published 2026-09-16**. CSV is accepted in place of the suggested TSV.

| File | Data rows | Columns |
|---|---:|---:|
| peptides.csv | 2,464 | 26 |
| interactions.csv | 24,934 | 44 |
| targets_and_families.csv | 3,390 | 37 |

Validation checked strict UTF-8 CSV parsing, consistent row widths, expected headers, nonempty key identifiers and matching release metadata. Copied bytes and SHA-256 were verified. Checksums and manual provenance are in versions.txt; exact file download URLs were not supplied, so only the known source page is recorded. The prior automated failure and run summary remain intact. Authenticated automated acquisition is still unfinished and no remote freshness check is claimed.

Raw assets are now available locally for **16/16 sources (45 files)**, including manual LRdb and GtoPdb imports. This is not a claim that all 16 automated adapters work. GtoPdb contains synthetic ligands, other species, missing species fields and multiple assay records per pair: its 24,934 rows are not a count of eligible unique LR pairs. Target species includes 19,957 Human and 1,243 Mouse records, but these counts do not establish matching ligand species or endogenous gene-encoded interactions. Preserve and assess both partners during later normalization. No filtering, conversion or biological validation was performed during import.

### Subsequent manual LRdb import

The user downloaded LRdb.txt from the linked author endpoint in a browser. It was validated and copied unchanged to data/sources/lrdb/LRdb.txt: 241,045 bytes, 3,639 records and 3,639 unique ordered ligand–receptor pairs. All records contain the four expected fields (ligand, receptor, d.ligand, d.receptor), with no missing endpoints or descriptions. SHA-256: `5174f35ad3851bcf66bc0f5d581ca4c9e10f6988429d6aeb37b1b06deec526a6`.

The central versions.txt records this as a manual import, with unknown upstream version and no claimed remote freshness verification. Automated LRdb access still has the TLS blocker below; the pipeline code was not changed. The preceding automated failure is retained as automated_access_status, and the prior automated run summary is unchanged. Local source availability is now 15/16 (42 files); GtoPdb remains pending. Validation establishes table integrity, not independent biological verification or proof of upstream completeness.

**14 of 16 sources acquired: 41 files, 88,275,810 bytes.** Final all-source repeat: **0 updated, 14 unchanged, 1 unavailable, 1 authentication-required, 0 failed**; exit code 1 as intended. The two inaccessible sources have no substituted historical data. An intermediate run hit GitHub's API quota; the final run successfully exercised the Git fallback. ICELLNET was corrected from its older software tag to its current data commit before the final repeat.

| Source | Available coverage | Result and qualification |
|---|---|---|
| CellCall | Human + mouse | Core/extended LR–TF files and KEGG lookup; mouse is provider homology-derived. |
| Cellinker | Human + mouse | Interaction and complex tables; native versus inferred evidence is not established here. Alias: Celllinker. |
| OmniPathPPIs | Human + mouse | `ligrecextra` interactions with sources/references; mouse is server orthology-derived. Human intercellular roles and complexes are stored once. |
| Dimitrov | Human only | LIANA V2.0.0 aggregate `omni_resource.csv`; consensus and constituent resources are retained together, unmodified. |
| CellPhoneDB | Human only | v5.0.0 interaction, gene, protein, complex and TF inputs. Alias: DellPhoneDB. |
| Kirouac | Human only | Original 2010 supplementary dataset and tables via Europe PMC. |
| CellChat | Human + mouse | Current official species database objects include complexes/cofactors/gene information; mixed/unknown evidence provenance. |
| ConnectomeDB | Human + mouse | Official Current-Release bulk catalog dated 2025-09-25; mouse is provider orthology-derived. Web-browser display dates are not substituted for bulk release dates. |
| iTALK | Human only | Author's raw LR database object. |
| LRdb | Not acquired; human expected | Current BulkSignalR-linked author endpoint fails TLS certificate verification. |
| Ramilowski | Human only | Original April 2015 `PairsLigRec.txt`. |
| Pavlicev | Human only | Original 2017 Supplemental Tables workbook via Europe PMC; retained whole. |
| NicheNet | Human + mouse | Zenodo 7074291 human/mouse LR-network objects only; mouse is provider orthology-derived. |
| GtoPdb | Not acquired; human/mouse expected | Download page redirects to login. Official REST documentation also requires an API key. |
| CellTalkDB | Human + mouse | v1.0 LR objects, manual annotations, gene and UniProt lookups; evidence provenance remains unknown. |
| ICELLNET | Human only | Current official `ICELLNETdb.tsv`, with subunits/families/references. |

No new orthology mapping or capitalization conversion is invoked. “Human + mouse” describes supplied assets, not proof of native experimental evidence in both species. OmniPath is a raw LR-oriented input, not a finished LR database: `ligrecextra` is the explicit selected scope, and the full `omnipath`/`pathwayextra` intracellular networks are not downloaded. Its human interpretation tables do not become native mouse annotations.

### Blockers and terms

- **LRdb:** `https://partage-dev.montp.inserm.fr:9192/CBSB/SignalR/resources/LRdb.txt` fails with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. This is the endpoint discovered in current BulkSignalR `R/zzz.R`. Obtain a corrected server chain or a legitimately trusted CA configuration, then retry. TLS is never disabled; the older December 2019 database is not silently substituted.
- **GtoPdb:** [download access](https://www.guidetopharmacology.org/download.jsp) needs registration/login, and the [REST API](https://www.guidetopharmacology.org/webServices.jsp) requires a provider-issued key in the `GTP-API-Key` header. No credentials were available. Version 1 records this blocker; authenticated bulk acquisition is not implemented or validated, so supplying a key alone will not complete this source. That adapter needs finishing once authorized access is available; any credentials must be read from environment variables, never committed.
- **Redistribution:** [ConnectomeDB's policy](https://connectomedb.org/docs/policy.html) assigns CC-BY-NC 4.0 to data and requires a separate commercial license, despite its download page saying MIT; the policy assigns MIT to software. Resolve that conflict before publishing data. OmniPath was queried with `license=academic` and has heterogeneous upstream restrictions. GtoPdb documents ODbL for the database and CC-BY-SA 4.0 for contents plus commercial access fees. Other provider/upstream terms require review; repository software licenses are not blanket data licenses. Nothing was pushed or published.

## Verification and preservation

16 automated tests passed: unchanged content, unversioned changes, missing/corrupt repair, safe 304 handling, invalid payload rejection, source-set failure preservation, immutable metadata, Git checksum mismatches, atomic log rollback, unchanged mtimes, selective archive extraction, crash-backup recovery, Git API quota fallback and species/scope metadata.

All 41 acquired files were independently checked against logged size and SHA-256. Before/after SHA-256 checks matched all **10 pre-existing historical/vault files**, including `docs/.obsidian` and the handoff. Existing working-tree deletions were preserved. This new note is the only addition to the vault.
