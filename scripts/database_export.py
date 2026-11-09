"""Canonical Parquet/Excel partitioning, reversible cell encoding and parity checks."""
from collections import defaultdict
import json
from pathlib import Path
import shutil
import subprocess
import os
import math

import openpyxl
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
from openpyxl.utils import get_column_letter
import pyarrow as pa
import pyarrow.parquet as pq

from database_build import SCHEMAS, ROOT, js, file_hash, digest_table
from database_excel import display_value


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def excel_value(value):
    """Encode lists and unsafe scalar strings reversibly without creating Excel formulas.
    
    Parameters
    ----------
    value : object
        Source or canonical value to interpret.
    
    Returns
    -------
    object
        Reversibly encoded Excel cell value.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return js(value)
    if isinstance(value, str):
        # Escape null-equivalent empty strings and control/formula-leading strings
        # with a reversible JSON envelope. Source text is never executed as a formula.
        if not value or value.startswith(('=', '+', '-', '@', '~json:')) or any(ord(c) < 32 for c in value):
            return '~json:' + js(value)
    return value


def readme_rows(sp):
    """Describe workbook interpretation and serialization for the selected species.
    
    Parameters
    ----------
    sp : str
        Species used for identity lookup or output partition.
    
    Returns
    -------
    list[dict]
        Workbook topic/description rows.
    """
    return [{'topic': k, 'description': v} for k, v in [
        ('Scope', sp.title() + ' gene-encoded ligand–receptor interactions and a separate required nonprotein/proxy companion. No species conversion.'),
        ('Policies', 'Accepted database policies N01–N04. Provider-derived mouse evidence is included with its inferred label; unknown evidence provenance remains unknown.'),
        ('Joins', 'interaction_id joins primary/companion to Assertions, Evidence and Regulators. record_key joins every evidence/regulator assertion to Assertions and the unchanged normalized source record.'),
        ('Readable IDs', 'LRI, ENT, MEM, REG, CDF, ANN, AST, EVD and SCX identify interactions, entities, memberships, regulators, definitions, annotations, assertions, evidence and source complexes. Six-digit minimum numbering spans all species in one build. IDs may change between releases. record_id and evidence_id supplement unchanged normalized keys; provider accessions are unchanged.'),
        ('Entities', 'ligand_entity_id and receptor_entity_id join Entities. Complex-Members links entity_id to member_entity_id. Complex-Definitions preserves source definitions and stoichiometry context.'),
        ('Review', 'Review contains unresolved and excluded species-resolved assertions. Provenance-only LIANA constituent rows remain in Assertions; they do not count as supporting sources.'),
        ('Shared review', 'Shared-Review.parquet, Shared-Assertions.parquet and Shared-Evidence.parquet retain unknown, mixed, cross-species and other-species records outside both workbooks.'),
        ('Traceability', 'source_file, source_table, source_row and source_record_id locate the original input. record_key joins data/interim/<source>/records.parquet, which retains every original field in raw_json.'),
        ('Source annotations', 'Source-prefixed columns summarize sorted distinct values from eligible assertions only. Source-Annotations keeps each provider field on its supplying record; join by interaction_id or record_key. Empty lists mean no eligible reported value. Explicit false values remain distinct from missing.'),
        ('Related pair', 'related_interaction_id on a review/provenance assertion identifies an eligible matching pair without counting that weak assertion as support.'),
        ('Evidence counts', 'source_count counts contributing datasets; direct_publication_count counts distinct direct PMID values. Provider-summary PMIDs have a separate count. Neither count measures independent replication.'),
        ('Symbols', 'Stable same-species IDs are preferred. Unique exact aliases can map locally. Unknown literal symbols match exactly and carry an unverified limitation. No case conversion or fuzzy matching.'),
        ('Complexes', 'Required subunits stay together. Unknown stoichiometry is not one. Incompatible ratios or assembly context keep separate entity IDs. CellChat regulators are not required members.'),
        ('Peptides and proxies', 'GtoPdb endogenous peptides retain molecular identities linked to encoding genes. Proxy genes are dependencies, not molecule identifiers. Missing product IDs are explicitly marked.'),
        ('Serialization', 'Approved Excel workbooks are a five-sheet display subset. Lists use semicolon-separated text; blank means no retained display value. Exact typed lists and provenance remain in Parquet. Literal strings are stored as text, never formulas. IDs stay text; accession aliases change headers only.'),
        ('Signs', 'sign_summary describes positive source assertions. Missing/unreported signs are null and blank in Excel. unknown requires an eligible explicit provider sign value. Conflicting assertions remain visible, and a reversed PPI edge never inherits its original sign.'),
        ('Limits', 'This is an evidence-preserving database build, not biological validation. Source-specific scope and unresolved definitions limit coverage; no historical reconstruction was performed.'),
    ]]


def partitions(tables):
    """Partition canonical rows into species workbooks and Shared Parquet audit tables.
    
    Parameters
    ----------
    tables : dict[str, list[dict]]
        Canonical tables or source inventory used by this operation.
    
    Returns
    -------
    dict
        Human, mouse and shared sheet specifications.
    """
    result = {}
    for sp, prefix in [('human', 'Human'), ('mouse', 'Mouse'), ('shared', 'Shared')]:
        selected = lambda s: s == sp if sp != 'shared' else s not in ('human', 'mouse')
        assertions = [a for a in tables['assertions'] if selected(a['species_group'])]
        keys = {a['record_key'] for a in assertions}
        spec = []
        def add(sheet, name, rows, schema):
            spec.append({'sheet': sheet, 'filename': name + '.parquet', 'rows': rows, 'schema': schema})
        if sp != 'shared':
            add('Ligand-Receptor', 'Ligand-Receptor-' + prefix + '-DB', [r for r in tables['interactions'] if r['species'] == sp and r['tier'] == 'primary'], 'interactions')
            add('Nonprotein-Proxy', prefix + '-Nonprotein-Proxy', [r for r in tables['interactions'] if r['species'] == sp and r['tier'] == 'companion'], 'interactions')
        add('Review', prefix + '-Review', [a for a in assertions if a['disposition'] in ('review', 'excluded')], 'assertions')
        add('Assertions', prefix + '-Assertions', assertions, 'assertions')
        add('Evidence', prefix + '-Evidence', [e for e in tables['evidence'] if e['record_key'] in keys], 'evidence')
        add('Source-Annotations', prefix + '-Source-Annotations', [a for a in tables['source_annotations'] if a['record_key'] in keys], 'source_annotations')
        add('Source-Members', prefix + '-Source-Members', [m for m in tables['source_members'] if selected(m['species'])], 'source_members')
        if sp != 'shared':
            entities = [e for e in tables['entities'] if e['species'] == sp]
            entity_ids = {e['entity_id'] for e in entities}
            add('Entities', prefix + '-Entities', entities, 'entities')
            add('Complex-Members', prefix + '-Complex-Members', [m for m in tables['memberships'] if m['entity_id'] in entity_ids], 'memberships')
            add('Complex-Definitions', prefix + '-Complex-Definitions', [d for d in tables['definitions'] if d['entity_id'] in entity_ids], 'definitions')
            add('Regulators', prefix + '-Regulators', [r for r in tables['regulators'] if r['record_key'] in keys], 'regulators')
            add('Sources', prefix + '-Sources', tables['sources'], 'sources')
            add('Readme', prefix + '-Readme', readme_rows(sp), 'readme')
        result[sp] = spec
    return result


def write_parquet(partitions, output):
    """Write typed Parquet partitions and verify their immediate read-back equality.
    
    Parameters
    ----------
    partitions : dict
        Species sheet/file specifications and canonical rows.
    output : Path
        Destination artifact or release directory.
    
    Returns
    -------
    list[dict]
        File hashes, semantic hashes and row counts.
    """
    metadata = []
    for specs in partitions.values():
        for spec in specs:
            path = output / spec['filename']
            table = pa.Table.from_pylist(spec['rows'], schema=SCHEMAS[spec['schema']])
            pq.write_table(table, path, compression='zstd')
            assert table.equals(pq.read_table(path)), str(path)
            metadata.append({'path': path.name, 'rows': len(table), 'sha256': file_hash(path), 'semantic_sha256': digest_table(spec['rows'], spec['schema'])})
    return metadata


def export_xlsx(specs, output, work, species, node=None):
    """Stream complete canonical tables into Excel with text identifiers and readable formatting.
    Full artifact-tool export exceeds its string limit at this volume; never truncate long evidence.
    
    Parameters
    ----------
    specs : list[dict]
        Ordered worksheet specifications with rows and schema names.
    output : Path
        Destination artifact or release directory.
    work : Path
        Disposable working directory; never a source-data directory.
    species : str
        Output species label; never an instruction to convert identities.
    node : str, optional
        Optional Node executable for previews only.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If any string exceeds the Excel cell limit; source evidence is never truncated.
    """
    book = openpyxl.Workbook(write_only=True)
    bodyfont = Font(name='Arial', size=10)
    headfont = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    for name, fmt in [('DataText','@'),('DataNumber','#,##0'),('DataBoolean','General')]:
        book.add_named_style(NamedStyle(name=name, font=bodyfont, number_format=fmt, alignment=Alignment(vertical='top', wrap_text=True)))
    book.add_named_style(NamedStyle(name='DataHeader',font=headfont,fill=PatternFill('solid',fgColor='203F60'),alignment=Alignment(wrap_text=True,vertical='center',horizontal='center')))
    for spec in specs:
        fields = spec.get('excel_fields', SCHEMAS[spec['schema']])
        sheet = book.create_sheet(spec['sheet'])
        if not spec.get('presentation'):
            sheet.freeze_panes = 'C2' if spec['sheet'] in ('Ligand-Receptor','Nonprotein-Proxy') else 'A2'
        sheet.sheet_view.showGridLines = False
        sheet.auto_filter.ref = 'A1:' + get_column_letter(len(fields)) + str(len(spec['rows']) + 1)
        if spec['sheet'] in ('Ligand-Receptor','Nonprotein-Proxy'):
            sheet.sheet_properties.tabColor = '203F60'
        widths = []
        for i, f in enumerate(fields, 1):
            width = 110 if spec['sheet']=='Readme' and i==2 else 25 if f.name in ('ligand','receptor','display_label','source_label') else 48 if any(v in f.name for v in ('description','reason','limitation','citation','context','identity')) or f.name=='value' else 38 if f.name.endswith(('_id','_key')) else 24
            widths.append(width)
            sheet.column_dimensions[get_column_letter(i)].width = width
        if spec.get('presentation'):
            sheet.freeze_panes = None
            sheet.auto_filter.ref = None
            sheet.sheet_view.showGridLines = True
            sheet.sheet_properties.tabColor = None
            widths = [style['width'] for style in spec['template_styles']]
            for i, width in enumerate(widths, 1):
                sheet.column_dimensions[get_column_letter(i)].width = width
        header = []
        for f in fields:
            c = WriteOnlyCell(sheet, f.name)
            c.style = 'DataHeader'
            if spec.get('presentation'):
                style = spec['template_styles'][len(header)]
                c.font, c.fill, c.border, c.alignment = style['font'], style['fill'], style['border'], style['alignment']
            header.append(c)
        sheet.row_dimensions[1].height = spec.get('header_height', 34)
        sheet.append(header)
        column_styles = ['DataNumber' if pa.types.is_integer(f.type) else 'DataBoolean' if pa.types.is_boolean(f.type) else 'DataText' for f in fields]
        for n, row in enumerate(spec['rows'], 2):
            cells = []
            height = 20
            for f, width, style in zip(fields, widths, column_styles):
                original = row.get(spec.get('field_map', {}).get(f.name, f.name))
                value = display_value(original) if spec.get('presentation') else excel_value(original)
                if isinstance(value,str) and len(value)>32767:
                    raise ValueError('Excel cell limit exceeded; refusing truncation')
                c = WriteOnlyCell(sheet, value)
                c.style = style
                if spec.get('presentation'):
                    c.alignment = Alignment(horizontal='left', vertical='center')
                if isinstance(value,str):
                    c.data_type = 's'
                    height = max(height, min(300, math.ceil(len(value)/max(1,width-2))*13))
                cells.append(c)
            sheet.row_dimensions[n].height = height
            sheet.append(cells)
        print('Excel ' + species + '/' + spec['sheet'] + ': ' + str(len(spec['rows'])) + ' rows', flush=True)
    book.save(output)


def render_previews(specs, work, species, node=None):
    """Render bounded worksheet examples using the optional Codex Node artifact runtime.
    These images assess layout only; full data integrity is checked independently.
    
    Parameters
    ----------
    specs : list[dict]
        Ordered worksheet specifications with rows and schema names.
    work : Path
        Disposable working directory; never a source-data directory.
    species : str
        Output species label; never an instruction to convert identities.
    node : str, optional
        Optional Node executable for previews only.
    
    Returns
    -------
    None
        Mutates the documented destination/context; returns no value.
    
    Raises
    ------
    ValueError
        If a sampled value exceeds the Excel cell limit; Node failures propagate separately.
    """
    runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    node = node or str(runtime / 'bin/node.exe')
    modules = runtime / 'node_modules'
    work.mkdir(parents=True, exist_ok=True)
    if not (work / 'node_modules').exists():
        if os.name == 'nt':
            # Fixed resolved paths supplied as literals; no filesystem deletion/moving.
            subprocess.run(['powershell', '-NoProfile', '-Command',
                "New-Item -ItemType Junction -Path '" + str(work / 'node_modules').replace("'", "''") + "' -Target '" + str(modules).replace("'", "''") + "' | Out-Null"], check=True)
        else:
            (work / 'node_modules').symlink_to(modules, target_is_directory=True)
    script = work / 'export_database_workbooks.mjs'
    shutil.copyfile(ROOT / 'scripts/export_database_workbooks.mjs', script)
    config = {'previewDir': str(work / 'previews' / species), 'sheets': []}
    for spec in specs:
        fields = spec.get('excel_fields', SCHEMAS[spec['schema']])
        rows = [[display_value(row.get(spec['field_map'][f.name])) if spec.get('presentation') else excel_value(row.get(f.name)) for f in fields] for row in spec['rows'][:6]]
        for row in rows:
            if any(isinstance(v, str) and len(v) > 32767 for v in row):
                raise ValueError('Excel cell limit exceeded; refusing truncation: ' + spec['sheet'])
        path = work / (species + '-' + spec['sheet'] + '.json')
        path.write_text(json.dumps({'columns': fields.names, 'types': ['number' if pa.types.is_integer(f.type) else 'boolean' if pa.types.is_boolean(f.type) else 'text' for f in fields], 'rows': rows}, ensure_ascii=False), encoding='utf-8')
        config['sheets'].append({'name': spec['sheet'], 'path': str(path)})
    config_path = work / (species + '-workbook.json')
    config_path.write_text(json.dumps(config), encoding='utf-8')
    with (work / (species + '-render.log')).open('w', encoding='utf-8') as log:
        subprocess.run([node, str(script), str(config_path)], check=True, cwd=work, stdout=log, stderr=log)


def validate_excel(path, specs):
    """Decode and compare every Excel cell with canonical values and check worksheet structure.
    
    Parameters
    ----------
    path : Path
        Local file or directory used by this operation.
    specs : list[dict]
        Ordered worksheet specifications with rows and schema names.
    
    Returns
    -------
    dict
        Passed status, sheet count and compared-cell count.
    """
    book = openpyxl.load_workbook(path, read_only=True, data_only=False)
    assert book.sheetnames == [s['sheet'] for s in specs], 'Workbook sheet mismatch'
    count = 0
    for spec in specs:
        sheet = book[spec['sheet']]
        fields = spec.get('excel_fields', SCHEMAS[spec['schema']])
        rows = sheet.iter_rows()
        assert [c.value for c in next(rows)] == fields.names
        n = 0
        for n, cells in enumerate(rows, 1):
            assert n <= len(spec['rows']), 'Extra Excel row'
            expected = spec['rows'][n - 1]
            for f, cell in zip(fields, cells):
                value = cell.value
                assert cell.data_type != 'f', 'Unexpected executable formula'
                expected_value = expected.get(spec.get('field_map', {}).get(f.name, f.name))
                if spec.get('presentation'):
                    expected_value = display_value(expected_value)
                elif value is not None and pa.types.is_list(f.type):
                    value = json.loads(value)
                elif isinstance(value, str) and value.startswith('~json:'):
                    value = json.loads(value[6:])
                assert value == expected_value, (spec['sheet'], n, f.name, value, expected_value)
                if pa.types.is_string(f.type) and value is not None:
                    assert isinstance(value, str), ('Identifier/text coercion', spec['sheet'], f.name)
            count += len(fields)
        assert n == len(spec['rows']), (spec['sheet'], n, len(spec['rows']))
    book.close()
    # Read structural XML directly, avoiding loading millions of cells just for layout.
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(path) as archive:
        for index, spec in enumerate(specs, 1):
            root = ET.fromstring(archive.read('xl/worksheets/sheet' + str(index) + '.xml'))
            if spec.get('presentation'):
                assert root.find('s:autoFilter',ns) is None
                assert root.find('s:sheetViews/s:sheetView/s:pane',ns) is None
                assert all(s.get('pane') in (None, 'topLeft') for s in root.findall('s:sheetViews/s:sheetView/s:selection',ns)), 'Selection references a nonexistent pane'
            else:
                assert root.find('s:autoFilter',ns) is not None
                assert root.find('s:sheetViews/s:sheetView/s:pane',ns).attrib['ySplit']=='1'
            assert root.find('s:cols',ns) is not None
    return {'status': 'passed', 'sheets': len(specs), 'cells_compared': count}
