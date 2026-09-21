"""Generate a review note from the completed per-source intermediates, without merging them."""
from collections import Counter
import json

import pyarrow.parquet as pq

from normalization_core import ROOT, SOURCE_IDS


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def fmt(value):
    """Format an integer for the generated normalization review tables.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    str
        Display count with thousands separators.
    """
    return f'{value:,}'


def write_report(manifest):
    """Write the generated source inspection report from current normalization metadata.
    
    Parameters
    ----------
    manifest : dict
        Recorded source selections, checksums and processing state.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    """
    entries = manifest['sources']
    successful = {s: entries[s] for s in SOURCE_IDS if entries.get(s, {}).get('status') == 'success'}
    rows = {s: pq.read_table(ROOT / 'data/interim' / s / 'records.parquet').to_pylist() for s in successful}
    lines = ['# Source normalization and decisions', '',
             '| Source | Retained raw records | Distinct semantic assertions | Human / mouse nonexcluded assertions | Unresolved records | Parsing / scope limitation |',
             '|---|---:|---:|---:|---:|---|']
    limits = {
        'cellcall': 'LR–TF/pathway rows; core and extended retained.',
        'cellinker': 'Complex IDs joined; native/inferred mouse evidence unknown.',
        'omnipathppis': 'PPI orientation unresolved for some human and all mouse rows.',
        'dimitrov': 'Consensus plus constituent memberships; not independent corroboration.',
        'cellphonedb': 'Non-LR pair classes and enzyme proxies retained for review.',
        'kirouac': '405 numeric mapping rows plus 232 unresolved S12 text assertions.',
        'cellchat': 'Nested R tables read; cofactors separate; nonprotein proxies typed.',
        'connectomedb': 'One ambiguous mouse receptor ID list; AI links are not experimental evidence.',
        'italk': '17 missing approved receptor symbols retained with source names and unknown partner species.',
        'lrdb': 'Manual import usable; no pair-level references.',
        'ramilowski': 'Putative rows and possible enzyme proxies remain review records.',
        'pavlicev': 'S5 only; reversed header order; exact proxy count not annotated.',
        'nichenet': 'Aggregate membership only; mouse orthology-derived.',
        'gtopdb': 'Pharmacology assays, unknown/mixed/cross species and explicit exclusions retained.',
        'celltalkdb': 'Same-species source IDs used; mouse evidence provenance unknown.',
        'icellnet': 'Required ligand/receptor subunits preserved together.',
    }
    for s in SOURCE_IDS:
        if s not in successful:
            lines.append(f"| {s} | — | — | — | — | BLOCKED: {entries.get(s, {}).get('error', 'not run')} |")
            continue
        q = successful[s]['summary']
        counts = q['nonexcluded_distinct_by_species']
        lines.append(f"| {s} | {fmt(q['normalized_records'])} | {fmt(q['distinct_semantic_interactions'])} | {fmt(counts['human'])} / {fmt(counts['mouse'])} | {fmt(q['unresolved_records'])} | {limits[s]} |")
    total = sum(v['summary']['normalized_records'] for v in successful.values())
    lines += ['', f"**{len(successful)}/16 sources normalized; {fmt(total)} interaction records retained.** Raw interaction counts reconcile one-to-one with normalized records: no interaction expansion, aggregation or row dropping. Repeated assays, LR–TF rows and evidence-membership rows remain separate. Supporting table counts/schemas, source checksums, releases and outputs are in `data/interim/manifest.json`.", '',
              '“Distinct semantic assertions” means a within-source key containing typed endpoint IDs, both species sets, complex identity and orientation. It is not a count of independently validated LR pairs. Unresolved Kirouac text assertions and pharmacology records are included in that column. Human/mouse counts require both endpoints to have the same single species and exclude explicit out-of-scope rows, but include records awaiting decisions. They are **candidate pools**, not approved masters. Counts across sources must not be added as unique pairs.', '',
              'An unresolved record has an absent or ambiguous necessary identifier. Untouched source symbols are separately labeled `source_symbol_unverified`; they have not been certified against modern gene nomenclature. Original whitespace/case and all source interaction fields remain in `raw_json`, with original endpoint labels retained separately. No sibling annotation resource or species translation was used.', '',
              '## N01 — Provider-derived mouse orthology', '',
              '**Recommendation:** retain provider-derived mouse interactions as a separately labeled inferred tier, with provenance and original source membership exposed in both future formats. Offer a native-evidence-only view only after record-level native support is established. Do not relabel the unknown-provenance tier as native.', '',
              '| Source | Mouse records | Known provider orthology | Unknown native/inferred provenance | Distinct mouse assertions |',
              '|---|---:|---:|---:|---:|']
    inferred = unknown = 0
    for s, records in rows.items():
        mouse = [r for r in records if r['species_group'] == 'mouse']
        if not mouse:
            continue
        i = sum(r['evidence_provenance'] == 'provider_orthology' for r in mouse)
        u = sum(r['evidence_provenance'] == 'unknown' for r in mouse)
        inferred += i
        unknown += u
        lines.append(f"| {s} | {fmt(len(mouse))} | {fmt(i)} | {fmt(u)} | {fmt(len({r['semantic_key'] for r in mouse}))} |")
    lines += ['', f'Across per-source rows, **{fmt(inferred)} known inferred mouse records** and **{fmt(unknown)} unknown-provenance mouse records** are distinguishable. These are overlapping source records, not a cross-source union. No mouse record is asserted here to have verified native experimental support. Human asset provenance labeled “native” is also not promoted automatically to pair-level experimental proof.', '',
              'Examples: CellCall homology LR–TF rows, ConnectomeDB `A2m → Lrp1` and the NicheNet mouse network keep the provider-orthology label. CellChat `Tgfb1 → TGFbR1_R2`, Cellinker mouse interactions and CellTalkDB mouse pairs remain unknown-provenance. ConnectomeDB mouse `Evidence=Direct` is retained verbatim but does not override the supplied dataset-level orthology provenance. GtoPdb `CCL19 → CCR7` with explicit Mouse/Mouse fields is species-compatible; provenance of native experimental support still requires evidence review.', '',
              '**Decision requested:** include inferred evidence as a labeled tier, or require a native-only final mouse scope (which needs additional provenance review rather than treating all unflagged rows as native).', '',
              '## N02 — Multi-subunit complexes', '',
              '**Recommendation:** one interaction connects complete endpoint entities. Keep required members in `memberships.parquet`; keep CellChat agonists, antagonists and activating/inhibitory co-receptors in `regulators.parquet`. Do not generate a Cartesian product of ligand and receptor subunits. Unknown alternatives remain unexpanded text.', '',
              '| Source | Records involving a declared complex | Records with ≥2 required members | Distinct assertions with ≥2 required members |',
              '|---|---:|---:|---:|']
    for s, entry in successful.items():
        q = entry['summary']
        if q['complex_records']:
            lines.append(f"| {s} | {fmt(q['complex_records'])} | {fmt(q['multisubunit_records'])} | {fmt(q['multisubunit_interactions'])} |")
    lines += ['', 'These counts exclude biosynthetic/transport proxy components from the required-protein-subunit count. A declared complex can contain one listed gene (for example a homomer with unprovided stoichiometry), so the two columns differ. Source-supplied stoichiometry stays available at the cited raw definition; missing stoichiometry is not invented.', '',
              'For example, a later Excel row could display `IL12A + IL12B → IL12RB1 + IL12RB2` with separate endpoint complex IDs and a membership sheet. Parquet would keep those same IDs plus four required-member rows; this is **one** interaction, not four. CellChat `TGFB1 → TGFbR1_R2` keeps `TGFBR1` and `TGFBR2` required while its antagonists remain regulator links. CellCall receptor commas are split only because its source implementation explicitly treats them as required complexes. NicheNet `C4B_2` remains one literal label. Kirouac S12 `ADIPOR 1/2` remains an unresolved alternative/complex assertion.', '',
              '**Decision requested:** preserve complex endpoints in the masters as recommended; decide separately how unresolved alternatives and incomplete complex definitions should appear. No subunit splitting has been performed in these intermediates.', '',
              '## N03 — Nonprotein ligands and enzyme proxies', '',
              '**Recommendation:** retain a gene-encoded LR view and a separate typed nonprotein/proxy view. A biosynthetic enzyme is a proxy for production, not the ligand molecule. If the expanded scope is selected later, keep molecule identifiers, proxy identifiers, dependency roles and measured species separate.', '',
              '| Source | Flagged nonprotein/proxy records | Distinct flagged assertions | Qualification |',
              '|---|---:|---:|---|']
    for s, entry in successful.items():
        q = entry['summary']
        if q['nonprotein_proxy_records']:
            qualification = 'Potential enzyme proxies based on ligand description; not a confirmed proxy count.' if s in ('lrdb', 'italk', 'ramilowski') else 'Includes retained pharmacological exclusions; use status before inclusion.' if s == 'gtopdb' else 'Explicit source proxy/nonprotein semantics.'
            lines.append(f"| {s} | {fmt(q['nonprotein_proxy_records'])} | {fmt(q['nonprotein_proxy_interactions'])} | {qualification} |")
    lines += ['', 'CellPhoneDB `Acetylcholine_byCHAT → CHRM1` remains a proxy entity whose component is CHAT; neither CHAT nor its UniProt accession is renamed acetylcholine. CellChat uses `annotation=Non-protein Signaling`, not `is_neurotransmitter`: that flag also marks protein pathways such as WNT. Four CellPhoneDB hCGB complex interactions have `is_ppi=False` despite protein-complex definitions; those conflicts are flagged rather than counted automatically as nonprotein ligands.', '',
              'Pavlicev S5 explicitly includes receptor–biosynthetic-enzyme associations but provides no per-row proxy flag. All 1,006 S5 records therefore retain a proxy-classification review flag, and the exact count of true proxies is **undetermined**. Examples `HSD3B1 → PAQR7` and `HSD17B2 → ESR1` remain original gene proxies/labels for review; no metabolite identity is invented. Labels such as `CCl19`, `FGF12B` and `SCYA*` remain unchanged.', '']
    if 'gtopdb' in rows:
        records = rows['gtopdb']
        raw = [json.loads(r['raw_json']) for r in records]
        endogenous = sum(str(r.get('Endogenous', '')).lower() == 'true' for r in raw)
        ep = sum(str(r.get('Endogenous', '')).lower() == 'true' and r.get('Ligand Type') == 'Peptide' for r in raw)
        groups = Counter(r['species_group'] for r in records)
        stats = successful['gtopdb']['summary']
        lines += [f"GtoPdb release **2026.3** contains **{fmt(len(records))} assay/interaction rows**, including **{fmt(endogenous)} Endogenous=true** and **{fmt(ep)} endogenous peptide rows** before species and entity review. Explicit pharmacological/out-of-scope exclusions retain **{fmt(stats['by_status'].get('excluded', 0))} rows** with reasons. Endogenous status and ligand type are distinct tests; metabolites can be endogenous.", '',
                  '| GtoPdb normalized endpoint species class | Records |', '|---|---:|']
        lines += [f'| {g} | {fmt(n)} |' for g, n in sorted(groups.items())]
        lines += ['', 'The missing ligand species on pharmacological molecules is not filled from target species. Multi-species peptide labels remain sets and are not expanded into species-specific pairs. Peptide subunit and target-subunit IDs use their respective GtoPdb namespaces. The local peptide table does not provide full small-molecule metadata; some target-as-ligand entities remain unresolved. Raw Action/Type values and repeated affinity measurements survive; agonism/binding is not converted into a universal activation sign.', '']
    lines += ['**Decision requested:** gene-encoded LR scope only, or include a separately typed nonprotein/proxy tier. Precise classification of Pavlicev proxies and missing small-molecule companion metadata remain follow-up work under either policy.', '',
              '## N04 — Additional decisions and evidence overlap', '',
              '- **Interaction scope/direction:** keep CellPhoneDB adhesion, gap-junction, ligand–ligand and receptor–receptor rows as a separate class or exclude them from the strict LR view. OmniPath source→target is a signaling edge, not always ligand→receptor. Unique human ligand/receptor-role matches are oriented; ambiguous and mouse edges stay unresolved. Unknown signs remain null, and conflicting positive signs are flagged. Reversing endpoints never transfers the original PPI sign to the reverse relation.',
              '- **Aggregate evidence:** use LIANA `resource=consensus` as the Dimitrov resource while preserving its constituent rows for provenance. OmniPath, LIANA, NicheNet and several curated databases overlap; database membership and repeated citations must not count as independent biological replication. LRdb and iTALK lack pair-level references; neither database citation is assigned to all rows. ConnectomeDB PubMed IDs embedded in provider summary links have a distinct evidence type.',
              '- **Species/identifier uncertainty:** decide whether mixed-species, cross-species, unspecified species, Kirouac free-text receptor alternatives, Ramilowski putative pairs and unresolved legacy symbols should be excluded from the strict view or retained in explicit review tiers. iTALK missing approved receptor symbols retain their names (including ECRF3 and US28) with unknown partner species; the human dataset label does not settle those endpoint species.', '',
              '## Reconciliation, validation and use', '',
              'Run `python scripts/normalize_sources.py --report` after installing `requirements-normalization.txt`; use `--source <id>` for a focused rebuild. See [Normalization usage](Normalization%20usage.md) for schema, provenance, failure behavior and tests. Each source has typed `records.parquet`, `evidence.parquet`, `memberships.parquet`, `regulators.parquet` and `review_examples.tsv`. Review extracts are samples, not a filtered replacement for the full intermediates.', '',
              'The command verifies all used raw input checksums before and after, verifies row reconciliation and unique record keys, validates typed Parquet roundtrips and resolves evidence/regulator and complex-membership references. Full-build repeat determinism and raw/vault preservation are recorded in `data/interim/validation.json` by the validation command. Per-source parse limitations are retained in the manifest. R tibble class notices mean conversion to data frames; all table counts, columns and row identities are retained. No R package source code is executed.', '',
              'All current local sources parse. LRdb/GtoPdb online acquisition blockers do not block these offline imports. The original files, `versions.txt`, historical data and existing Obsidian notes/settings remain unchanged. **Final human/mouse master XLSX and Parquet generation is deferred until N01–N03 and the substantive N04 scope decisions are resolved.**', '',
              'Source-semantics references: [CellCall required receptor complexes](https://github.com/ShellyCoder/cellcall/blob/master/R/data2ConnectProfile.R), [CellChat database structure](https://github.com/jinworks/CellChat), plus the local CellPhoneDB complex/protein tables, GtoPdb release headers and Pavlicev S5 preamble. Acquisition citations/terms remain in the unmodified source manifest; they are dataset provenance, not pair evidence.', '']
    path = ROOT / 'docs/Source normalization and decisions.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
