"""Project complete canonical tables into the approved reader-facing workbook."""
from copy import copy
import hashlib
import json
from pathlib import Path

import openpyxl
import pyarrow as pa

from normalization_core import ROOT, file_hash
from normalization_core import js

TEMPLATE_ROOT = ROOT / 'data/templates'
ALIASES = {'gene_accession': 'gene_id'}


# =============================================================================
# Template-backed Excel projection
# =============================================================================
def workbook_partitions(pieces: dict, schemas: dict, template_root: Path = TEMPLATE_ROOT) -> tuple[dict, list[dict]]:
    """Select template sheets without removing any canonical Parquet records.

    Parameters
    ----------
    pieces : dict
        Complete species partitions used for Parquet export.
    schemas : dict
        Canonical Arrow schemas.
    template_root : Path, optional
        Directory containing the approved template pair and manifest.

    Returns
    -------
    tuple[dict, list[dict]]
        Excel-only specifications and hashed template inputs.

    Raises
    ------
    ValueError
        If template bytes, sheets, headers or fields disagree with the manifest.
    """
    manifest_path = template_root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    inputs = [{'path': str(manifest_path.resolve()), 'sha256': file_hash(manifest_path)}]
    result = {}
    for species in ('human', 'mouse'):
        entry = next(f for f in manifest['files'] if f['species'] == species)
        path = template_root / entry['path']
        if path.parent.resolve() != template_root.resolve() or file_hash(path) != entry['sha256']:
            raise ValueError('Template path or checksum mismatch: ' + entry['path'])
        inputs.append({'path': str(path.resolve()), 'sha256': entry['sha256']})
        book = openpyxl.load_workbook(path)
        try:
            if book.sheetnames != [s['name'] for s in manifest['sheets']]:
                raise ValueError('Template sheet mismatch')
            available = {spec['sheet']: spec for spec in pieces[species]}
            result[species] = []
            for sheet in manifest['sheets']:
                ws = book[sheet['name']]
                columns = sheet['headers']
                headers = [cell.value for cell in ws[1]]
                while headers and headers[-1] is None:
                    headers.pop()
                if headers != columns:
                    raise ValueError('Template header mismatch: ' + sheet['name'])
                if any(c.value is not None for row in ws.iter_rows(min_row=2) for c in row):
                    raise ValueError('Template must contain headers only')
                spec = available[sheet['name']]
                source_fields = schemas[spec['schema']]
                mapping = {name: ALIASES.get(name, name) for name in columns}
                if not set(mapping.values()) <= set(source_fields.names):
                    raise ValueError('Unrecognized template field: ' + sheet['name'])
                fields = pa.schema([pa.field(name, source_fields.field(mapping[name]).type) for name in columns])
                styles = []
                for index in range(1, len(columns) + 1):
                    cell = ws.cell(1, index)
                    width = ws.sheet_format.defaultColWidth or 13
                    for dim in ws.column_dimensions.values():
                        if dim.min <= index <= dim.max:
                            width = dim.width
                            break
                    styles.append({'font': copy(cell.font), 'fill': copy(cell.fill),
                                   'border': copy(cell.border), 'alignment': copy(cell.alignment), 'width': width})
                rows = spec['rows']
                if sheet['name'] == 'Regulators':
                    # The input view has no disposition column: excluded/review
                    # regulators must not appear to support accepted interactions.
                    rows = [r for r in rows if r['disposition'] in ('primary', 'companion')]
                result[species].append({**spec, 'rows': rows, 'excel_fields': fields, 'field_map': mapping,
                                        'presentation': True, 'template_styles': styles,
                                        'header_height': ws.row_dimensions[1].height or 24})
        finally:
            book.close()
    return result, inputs


def display_value(value: object) -> object:
    """Format Excel-only lists as readable text, keeping absent values blank.

    Parameters
    ----------
    value : object
        Canonical typed value. Literal strings are never interpreted as formulas.

    Returns
    -------
    object
        Semicolon-separated list, blank for an empty list, or unchanged scalar.
        This is a display projection; Parquet retains exact list boundaries.
    """
    if isinstance(value, list):
        return '; '.join(str(item) for item in value) or None
    return None if value == '' else value


def digest_workbook(specs: list[dict]) -> str:
    """Hash projected values incrementally without duplicating the full workbook.

    Parameters
    ----------
    specs : list[dict]
        Ordered, template-backed Excel sheet specifications.

    Returns
    -------
    str
        SHA-256 of sheet names, column order and displayed row values.
    """
    digest = hashlib.sha256()
    for spec in specs:
        fields = spec['excel_fields'].names
        digest.update((js([spec['sheet'], fields]) + '\n').encode('utf-8'))
        for row in spec['rows']:
            values = [display_value(row.get(spec['field_map'][field])) for field in fields]
            digest.update((js(values) + '\n').encode('utf-8'))
    return digest.hexdigest()
