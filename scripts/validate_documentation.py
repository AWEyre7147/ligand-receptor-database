"""Check maintained documentation, reference pins, local links and public API docs offline."""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import re
from urllib.parse import unquote
from normalization_core import ROOT, file_hash
from database_identity import ANNOTATIONS

# =============================================================================
# Documentation and reference-asset checks
# =============================================================================

def check_annotations(annotation_dir: Path, pin_path: Path = ROOT / 'config/annotation-reference.json') -> int:
    """Verify the three identity assets against the repository's explicit pin.

    Parameters
    ----------
    annotation_dir : Path
        Directory containing manifest.json and the two species Parquet files.
    pin_path : Path
        Reviewed path-to-SHA256 reference catalog.

    Returns
    -------
    int
        Number of verified assets; no annotation data are copied or modified.

    Raises
    ------
    AssertionError
        If any reference bytes differ from the reviewed pin.
    OSError
        If required reference files are unavailable.
    """
    pin=json.loads(pin_path.read_text(encoding='utf-8'))
    for name,digest in pin['files'].items():
        assert file_hash(annotation_dir/name)==digest, 'Pinned annotation mismatch: '+name
    return len(pin['files'])


def check_links() -> int:
    """Resolve local Markdown and Obsidian links without requesting remote pages.

    Returns
    -------
    int
        Number of checked local link targets.

    Raises
    ------
    AssertionError
        If a local documentation target is missing.
    """
    count=0; failures=[]
    paths=list(ROOT.glob('*.md'))+list((ROOT/'docs').rglob('*.md'))+list((ROOT/'handoffs').glob('*.md'))
    for path in paths:
        if '.obsidian' in path.parts or 'archived' in path.parts: continue
        text=path.read_text(encoding='utf-8')
        text=re.sub(r'```.*?```','',text,flags=re.S)
        for target in re.findall(r'\]\(([^)]+)\)',text):
            target=target.strip('<>')
            if target.startswith(('https:','http:','mailto:','#','app:')): continue
            target=unquote(target.split('#')[0])
            # Historical notes intentionally record absolute local paths; test existence
            # but publication review must still redact them separately.
            resolved=(path.parent/target).resolve()
            if not resolved.exists(): failures.append(path.relative_to(ROOT).as_posix()+': '+target)
            count+=1
        for target in re.findall(r'\[\[([^\]]+)\]\]',text):
            target=target.split('|')[0].split('#')[0]
            if not any(p.stem==target or p.relative_to(ROOT/'docs').as_posix()==target+'.md' for p in (ROOT/'docs').rglob('*.md') if 'archived' not in p.parts):
                failures.append(path.relative_to(ROOT).as_posix()+': '+target)
            count+=1
    assert not failures, 'Broken local links: '+json.dumps(failures)
    return count


def check_public_docs() -> int:
    """Check maintained public function docstrings and script inventory coverage.

    Returns
    -------
    int
        Number of documented public Python functions/methods.

    Raises
    ------
    AssertionError
        If a public API lacks applicable NumPy sections or a script lacks a guide entry.
    """
    guide=(ROOT/'docs/Script guide.md').read_text(encoding='utf-8')
    count=0
    for path in sorted((ROOT/'scripts').glob('*')):
        if path.suffix not in ('.py','.mjs','.R'): continue
        assert path.name in guide, 'Missing script guide entry: '+path.name
        if path.suffix!='.py': continue
        tree=ast.parse(path.read_text(encoding='utf-8'))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        nodes += [n for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef)]
        for node in nodes:
            if node.name.startswith('_') and node.name!='__init__': continue
            doc=ast.get_docstring(node) or ''
            assert 'Returns\n-------' in doc, (path.name,node.name,'Returns')
            args=[a.arg for a in node.args.args+node.args.kwonlyargs if a.arg not in ('self','cls')]
            if args: assert 'Parameters\n----------' in doc,(path.name,node.name,'Parameters')
            if any(isinstance(n,ast.Raise) and n.exc is not None for n in ast.walk(node)):
                assert 'Raises\n------' in doc,(path.name,node.name,'Raises')
            count+=1
    for path in (ROOT/'tests').glob('*.py'): assert path.name in guide, 'Missing test guide entry: '+path.name
    return count


def main() -> None:
    """Run local documentation checks with an explicit annotation location.

    Returns
    -------
    None
        Prints counts after all checks pass; exceptions exit nonzero.
    """
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotation-dir',type=Path,default=ANNOTATIONS,help='Pinned same-species reference directory; default sibling annotations')
    args=parser.parse_args()
    print(json.dumps({'reference_assets':check_annotations(args.annotation_dir),'local_links':check_links(),'public_functions':check_public_docs()},indent=2))


if __name__=='__main__':
    main()
