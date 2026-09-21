# Repository readiness

Preparation milestone 004 is implemented locally. No remote was created, no commit/push/publication was performed, and no history or Git LFS migration was attempted. Scientific-policy changes are outside this milestone. Final verification details are recorded below after the full rebuild.

## Publication decision

The repository is ready for local review, **not yet cleared for public upload**. Code-license choice, third-party data redistribution, historical Git data, personal paths and the unpublished annotation dependency remain release prerequisites. These do not prevent using the verified local databases.

## Official terms checked

Official pages were checked during this milestone (2026-09-20 local session date). This is a record of publication conditions, not an invented blanket permission.

| Resource | Verified official position | Public inclusion decision |
|---|---|---|
| Project code | The tracked historical LICENSE is zero bytes; it establishes no intended license | Owner must choose/confirm a code license and attribution. No license was selected on the owner's behalf |
| ConnectomeDB | [Download page](https://connectomedb.org/downloads.html) says MIT for interaction data. [Policy page](https://connectomedb.org/docs/policy.html) specifies CC-BY-NC 4.0 for data, separate commercial permission, and MIT for website/software | Conflict remains unresolved. Withhold originals and derived records until owner/provider clarification and an appropriate notice/distribution scope are established |
| OmniPath | [Official FAQ](https://omnipathdb.org/) says original resources carry their own licenses; [resource metadata](https://omnipathdb.org/info) lists heterogeneous terms. Local query used academic access | Academic access is not blanket public redistribution permission. Review originating resources and downstream/aggregate overlap before any data release |
| GtoPdb | [Official downloads](https://www.guidetopharmacology.org/download.jsp) and [web services](https://www.guidetopharmacology.org/webServices.jsp) specify ODbL for the database and CC-BY-SA 4.0 for contents; provider access requires the authorized route | Resolve attribution/share-alike/database obligations and compatibility with the intended combined release. Do not equate access credentials with redistribution permission; withhold combined outputs pending review |
| Other 13 sources and upstream memberships | Official provider/citation/terms links are retained in source_registry.py and acquisition metadata; software licenses alone do not establish coverage of original or incorporated data | No complete per-asset redistribution clearance was established in this milestone. Withhold those originals and derived rows until a license/attribution matrix is approved |
| Same-species annotation assets | Three separate local reference files are pinned; source/reference-project terms and a stable retrieval route are not bundled | Obtain authorized files from their owner; do not copy the sibling project into this repository or claim standalone clone reproducibility |
| Historical data | Old processed tables remain in reachable Git history even though deleted in the current working tree; data/historical is preserved locally | Review legacy dataset redistribution and author/privacy metadata before any push of existing history. A clean current tree does not remove historical content |

## Explicit public-file inclusion plan

This is a proposed inclusion list, not a staging or publication action. **Do not use `git add -A`** for a release candidate.

1. After code-license approval, review/include project-owned `scripts/*.py`, `scripts/*.mjs`, `tests/*.py`, root README/AGENTS/.gitignore and requirements files. Test data are small synthetic fixtures in code, not copies of original databases. Add the chosen license/attribution only after owner decision.
2. Review/include generic setup and schema documentation plus curated config metadata. `config/annotation-reference.json` contains relative reference names and hashes, not the annotation data. The field guide, vocabulary catalog, source mappings and generated reports contain selected source-derived examples/labels/counts: include them only after the same applicable data-term review. Redact personal paths in narrative notes first and rerun link checks.
3. **Withhold all `data/sources`, `data/interim`, `data/processed`, `data/historical` and their manifests** from the initial public candidate until per-source/derived-data terms and attribution are resolved. Preserve them locally. Build input manifests contain absolute local paths and are not public-ready provenance bundles.
4. Keep `.venv`, temporary environments, scratch renders/logs, caches, `.obsidian`, credentials and personal editor state local. .gitignore handles these without blanket-ignoring scientific data. Keep useful handoffs locally/indexed; privacy-review them before public inclusion.
5. Audit existing Git history separately. Obtain owner authorization for a clean publication repository/export or any necessary history remediation; none was performed here. Do not push existing history simply because selected new files are safe.

Users can obtain cleared raw inputs from the official providers linked in the registry and preserve the recorded version/checksums. Automated acquisition supports accessible providers; LRdb may require a verified author download because of TLS failure, and GtoPdb requires authorized access/manual import because authenticated refresh is not implemented. Never disable TLS or commit credentials. The exact annotation trio must be obtained from its owner and checked against config/annotation-reference.json. There is currently no verified public command that reconstructs that trio.

## Remaining steps before upload

- Select/confirm the project code license and attribution.
- Resolve ConnectomeDB's conflicting terms; complete per-source/upstream and derived-output license/attribution review, including GtoPdb and academic OmniPath data.
- Establish lawful, versioned retrieval/distribution of the pinned annotation assets, or document an explicitly controlled-access dependency.
- Choose an owner-approved approach to legacy Git data/history and redact personal paths from the chosen publication files.
- Create an explicit staged file list, inspect staged content/history and rerun tests, guide/link checks and credential screening on that exact candidate. Excluded data links should be described as locally acquired artifacts in the public README.
- Choose a release-asset or external archival location for permitted large scientific artifacts if they are later cleared. Create a remote/commit/push only on a separate explicit instruction.

## Validation, preservation, sizes and cleanup

Full verification and measured sizes are being recorded in this section. The companion [audit record](audits/repository-audit.json) contains bounded secret-pattern screening results and file inventory, without secret values. A clean pattern scan is not a guarantee against every possible credential format.
