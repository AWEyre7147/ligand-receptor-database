"""All source definitions and official discovery rules; no species conversion."""
import html
import re
from urllib.parse import quote, urlencode, urljoin

from download_sources import AuthenticationRequired, RateLimited, Unavailable, fetch, get_json


# =============================================================================
# Public workflow and supporting operations
# =============================================================================
def definition(name, provider, citation, coverage, notes='', aliases=(), terms=None):
    """Describe a provider and its acquisition scope without granting redistribution rights.
    
    Parameters
    ----------
    name : str
        Schema, field or provider name selected by the caller.
    provider : str, optional
        Original evidence provider or official provider URL.
    citation : str
        Provider citation URL.
    coverage : str
        Provider-declared species coverage, without conversion.
    notes : str or sequence[str]
        Explicit scope or unresolved identity limitations.
    aliases : sequence[str]
        Alternative registered provider names.
    terms : str, optional
        Official redistribution terms URL.
    
    Returns
    -------
    dict
        Provider metadata including a redistribution-review notice.
    """
    return {'name': name, 'provider': provider, 'citation_url': citation,
            'terms_url': terms or provider, 'coverage': coverage, 'notes': notes,
            'aliases': list(aliases),
            'redistribution': 'Review provider and upstream data terms before public redistribution; software license is not a blanket data license.'}


SOURCES = {
    'cellcall': definition('CellCall', 'https://github.com/ShellyCoder/cellcall', 'https://doi.org/10.1093/nar/gkab638', 'human, mouse',
                           'Core and extended LR-TF references; mouse homology files are provider-derived, not native mouse experimental evidence.'),
    'cellinker': definition('Cellinker', 'https://www.rna-society.org/cellinker/Download.html', 'https://www.rna-society.org/cellinker/', 'human, mouse',
                            'Provider species-specific interactions and complexes; evidence provenance is mixed/unknown.', ('Celllinker',)),
    'omnipathppis': definition('OmniPathPPIs', 'https://omnipathdb.org/', 'https://doi.org/10.1038/s41592-018-0111-x', 'human, mouse',
                               'Raw ligrecextra interactions, intercellular roles and complex definitions. Not a finished LR database. Server mouse interactions are orthology-derived; no client translation. Human intercellular/complex tables are shared interpretation assets, not mouse-native annotations.', terms='https://omnipathdb.org/info'),
    'dimitrov': definition('Dimitrov', 'https://github.com/saezlab/liana-py', 'https://doi.org/10.1038/s41467-022-30755-0', 'human-only',
                           'LIANA aggregate distribution: omni_resource.csv contains consensus plus constituent resources. Retained intact; select resource=consensus downstream.'),
    'cellphonedb': definition('CellPhoneDB', 'https://github.com/ventolab/cellphonedb-data', 'https://doi.org/10.1038/s41596-020-0292-x', 'human-only', aliases=('DellPhoneDB',)),
    'kirouac': definition('Kirouac', 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC2990637/fullTextXML', 'https://doi.org/10.1038/msb.2010.71', 'human-only',
                          'Original publication supplementary dataset and tables, distributed by Europe PMC. Static 2010 resource.', terms='https://pmc.ncbi.nlm.nih.gov/articles/PMC2990637/'),
    'cellchat': definition('CellChat', 'https://github.com/jinworks/CellChat', 'https://doi.org/10.1038/s41467-021-21246-9', 'human, mouse',
                           'Current official data commit (software release tags lag database updates). Species-specific R objects include interactions, complexes, cofactors and gene information; mixed evidence, native/orthology split not established.'),
    'connectomedb': definition('ConnectomeDB', 'https://connectomedb.org/downloads.html', 'https://doi.org/10.1093/nar/gkaf1108', 'human, mouse',
                               'Official Current-Release human and orthology-mapped mouse files. Download catalog and web browser dates may differ; select bulk catalog.', terms='https://connectomedb.org/docs/policy.html'),
    'italk': definition('iTALK', 'https://github.com/Coolgenome/iTALK', 'https://doi.org/10.1101/507871', 'human-only'),
    'lrdb': definition('LRdb', 'https://github.com/jcolinge/BulkSignalR', 'https://doi.org/10.1093/nar/gkaa183', 'human-only',
                       'Current author distribution discovered from BulkSignalR R/zzz.R; not the frozen SCA-IRCM December 2019 snapshot.'),
    'ramilowski': definition('Ramilowski', 'https://fantom.gsc.riken.jp/5/suppl/Ramilowski_et_al_2015/', 'https://doi.org/10.1038/ncomms8866', 'human-only',
                             'Static April 2015 publication data; retain putative and literature-supported rows.'),
    'pavlicev': definition('Pavlicev', 'https://genome.cshlp.org/content/27/3/349/suppl/DC1', 'https://doi.org/10.1101/gr.207597.116', 'human-only',
                           'Original Supplemental Tables workbook from publication via Europe PMC; workbook retained whole, including supporting tables.', terms='https://pmc.ncbi.nlm.nih.gov/articles/PMC5340963/'),
    'nichenet': definition('NicheNet', 'https://github.com/saeyslab/nichenetr', 'https://doi.org/10.1038/s41592-019-0667-5', 'human, mouse',
                           'Current documented Zenodo LR-network models only. Mouse model is provider orthology-derived; no new conversions.', terms='https://zenodo.org/records/7074291'),
    'gtopdb': definition('GtoPdb', 'https://www.guidetopharmacology.org/download.jsp', 'https://www.guidetopharmacology.org/', 'shared (human and mouse; not acquired until authenticated)',
                         'Public download page currently requires login. No credentials are inferred or authentication bypassed.', terms='https://www.guidetopharmacology.org/about.jsp'),
    'celltalkdb': definition('CellTalkDB', 'https://github.com/ZJUFanLab/CellTalkDB', 'https://doi.org/10.1093/bib/bbaa269', 'human, mouse',
                             'Provider database objects and manual annotation/gene/protein lookup assets; species-specific evidence provenance remains unknown.'),
    'icellnet': definition('ICELLNET', 'https://github.com/soumelis-lab/ICELLNET', 'https://doi.org/10.1038/s41467-021-21244-x', 'human-only',
                           'Current official data commit as linked by Vignette.md (software release tags lag database updates). Human source table includes subunits, families and references; no mouse conversion.'),
}

SOURCES['connectomedb']['redistribution'] = ('Terms page specifies CC-BY-NC 4.0 for data and a separate commercial license; '
    'download page says MIT, while policy assigns MIT to software. Treat this conflict as unresolved before public redistribution.')
SOURCES['omnipathppis']['redistribution'] = ('Acquired with license=academic. Underlying resources have heterogeneous terms; '
    'academic access is not blanket permission for public or commercial redistribution.')
SOURCES['gtopdb']['redistribution'] = ('Official web-services documentation specifies ODbL for the database and CC-BY-SA 4.0 '
    'for contents, with registration/API keys and commercial access fees.')
SOURCES['gtopdb']['terms_url'] = 'https://www.guidetopharmacology.org/webServices.jsp'


def asset(url, species='human', provenance='unknown', name=None, **kwargs):
    """Describe an original download and its provider-declared species/provenance.
    
    Parameters
    ----------
    url : str
        Official provider URL, without embedded credentials.
    species : str
        Output species label; never an instruction to convert identities.
    provenance : str, optional
        Provider provenance label; absent is not native experimental proof.
    name : str
        Schema, field or provider name selected by the caller.
    kwargs : dict
        Additional source asset metadata.
    
    Returns
    -------
    dict
        Download URL, original filename and species/provenance metadata.
    """
    from urllib.parse import unquote, urlsplit
    return {'url': url, 'name': name or unquote(urlsplit(url).path.rsplit('/', 1)[-1]),
            'species': species, 'provenance': provenance, **kwargs}


def repo_state(repo, prefer_release=True):
    """Resolve an official release or commit, falling back to Git only on API rate limits.
    
    Parameters
    ----------
    repo : str
        Official GitHub owner/repository name.
    prefer_release : bool
        Prefer an official release where available; otherwise use a commit.
    
    Returns
    -------
    tuple
        Version selection metadata and repository path-to-blob mapping.
    """
    try:
        return api_repo_state(repo, prefer_release)
    except RateLimited:
        return git_repo_state(repo, prefer_release)


def git_repo_state(repo, prefer_release):
    """Resolve remote Git refs without cloning or downloading repository history.
    
    Parameters
    ----------
    repo : str
        Official GitHub owner/repository name.
    prefer_release : bool
        Prefer an official release where available; otherwise use a commit.
    
    Returns
    -------
    tuple
        Version selection and required repository paths resolved through Git.
    
    Raises
    ------
    Unavailable
        If the release/ref cannot be resolved, Git is unavailable/times out, or the fallback command fails.
    """
    import os
    import subprocess
    release = None
    if prefer_release:
        try:
            _, final = page('https://github.com/' + repo + '/releases/latest')
            if '/releases/tag/' not in final:
                raise Unavailable('Latest release page did not resolve to a tag')
            from urllib.parse import unquote
            release = unquote(final.split('/releases/tag/', 1)[1])
        except Unavailable as exc:
            if 'HTTP 404' not in str(exc):
                raise
    refs = ['refs/tags/' + release, 'refs/tags/' + release + '^{}'] if release else ['HEAD']
    try:
        result = subprocess.run(['git', '-c', 'credential.interactive=never', 'ls-remote',
                                 'https://github.com/' + repo + '.git', *refs],
                                capture_output=True, text=True, timeout=60,
                                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise Unavailable('GitHub API quota exhausted; Git fallback unavailable/timed out. Install Git or set GITHUB_TOKEN.') from None
    if result.returncode:
        raise Unavailable('GitHub API quota exhausted and git ls-remote failed; retry later or set GITHUB_TOKEN')
    resolved = {line.split()[1]: line.split()[0] for line in result.stdout.splitlines() if line.strip()}
    commit = resolved.get(refs[-1]) or resolved.get(refs[0])
    if not commit or not re.fullmatch('[0-9a-f]{40}', commit):
        raise Unavailable('Git did not return a commit for the selected ref')
    selection = {'repository': repo, 'release': release, 'commit': commit,
                 'selection_policy': 'latest official release' if release else 'current official repository commit',
                 'discovery_method': 'git ls-remote (GitHub API quota fallback)'}
    # These are the validated original paths, not substitute or cached datasets.
    paths = {
        'ShellyCoder/cellcall': ['inst/extdata/new_ligand_receptor_TFs' + suffix + '.txt' for suffix in ['', '_extended', '_homology', '_homology_extended']] + ['inst/extdata/KEGG_SYMBOL_ID.txt'],
        'ventolab/cellphonedb-data': ['data/' + kind + '_input.csv' for kind in ['complex', 'gene', 'interaction', 'protein', 'transcription_factor']],
        'jinworks/CellChat': ['data/CellChatDB.' + s + '.rda' for s in ['human', 'mouse']],
        'Coolgenome/iTALK': ['data/LR_database.rda'],
        'ZJUFanLab/CellTalkDB': ['database/' + s + '_lr_pair.rds' for s in ['human', 'mouse']] + ['data/' + s + '_' + kind + '.rds' for s in ['human', 'mouse'] for kind in ['ann_manual', 'gene2ensembl', 'gene_info', 'uniprot']],
        'soumelis-lab/ICELLNET': ['data/ICELLNETdb.tsv'],
        'saezlab/liana-py': ['src/liana/resource/omni_resource.csv'],
    }.get(repo, [])
    return selection, {path: None for path in paths}


def api_repo_state(repo, prefer_release=True):
    """Discover release/commit metadata through the authenticated-or-public GitHub API.
    
    Parameters
    ----------
    repo : str
        Official GitHub owner/repository name.
    prefer_release : bool
        Prefer an official release where available; otherwise use a commit.
    
    Returns
    -------
    tuple
        Release/commit selection and repository path-to-blob mapping.
    
    Raises
    ------
    ValueError
        If the provider returns a truncated repository tree; API errors propagate.
    """
    base = 'https://api.github.com/repos/' + repo
    release = None
    if prefer_release:
        try:
            release = get_json(base + '/releases/latest')['tag_name']
        except Unavailable as exc:
            if 'HTTP 404' not in str(exc):
                raise
    commit = get_json(base + '/commits/' + quote(release or 'HEAD', safe=''))['sha']
    tree = get_json(base + '/git/trees/' + commit + '?recursive=1')
    if tree.get('truncated'):
        raise ValueError('Truncated repository tree')
    blobs = {item['path']: item['sha'] for item in tree['tree'] if item['type'] == 'blob'}
    return {'repository': repo, 'release': release, 'commit': commit,
            'selection_policy': 'latest official release' if release else 'current official repository commit'}, blobs


def repo_assets(repo, select, species_for=lambda p: ('human', 'unknown'), prefer_release=True):
    """Select original repository assets at one immutable resolved commit.
    
    Parameters
    ----------
    repo : str
        Official GitHub owner/repository name.
    select : callable
        Predicate selecting required original assets.
    species_for : callable
        Assign provider-defined asset species metadata.
    prefer_release : bool
        Prefer an official release where available; otherwise use a commit.
    
    Returns
    -------
    tuple
        Resolved version metadata and selected original assets.
    
    Raises
    ------
    Unavailable
        If no required original asset paths exist in the selected repository version.
    """
    selection, blobs = repo_state(repo, prefer_release)
    paths = select(blobs)
    if not paths or any(p not in blobs for p in paths):
        raise Unavailable('Required data paths missing in selected repository release')
    assets = [asset('https://raw.githubusercontent.com/' + repo + '/' + selection['commit'] + '/' + quote(p),
                    *species_for(p), upstream_checksum='git-blob:' + blobs[p] if blobs[p] else 'git-commit:' + selection['commit'] + ':' + p) for p in paths]
    return selection, assets


def page(url):
    """Read an official discovery page without weakening TLS validation.
    
    Parameters
    ----------
    url : str
        Official provider URL, without embedded credentials.
    
    Returns
    -------
    tuple
        UTF-8 provider page text and final redirect URL.
    
    Raises
    ------
    AuthenticationRequired
        If discovery redirects to a provider login page.
    """
    data, _, final = fetch(url)
    if 'login' in final.lower():
        raise AuthenticationRequired('Provider requires login: ' + final)
    return data.decode('utf-8'), final


def links(text, base):
    """Resolve HTML download links relative to their provider page.
    
    Parameters
    ----------
    text : str
        Original page text.
    base : str
        Final provider page URL used to resolve relative links.
    
    Returns
    -------
    list[str]
        Absolute links discovered in the page.
    """
    return [urljoin(base, html.unescape(link)) for link in re.findall(r'href=[\"\']([^\"\']+)', text, re.I)]


def resolve(source):
    """Resolve the selected provider into version metadata and original asset descriptors.
    
    Parameters
    ----------
    source : str
        Registered provider identifier.
    
    Returns
    -------
    tuple
        Provider version selection and original asset descriptors.
    
    Raises
    ------
    KeyError
        For unknown source IDs (KeyError) or absent/unsupported official asset discovery (Unavailable).
    Unavailable
        For unknown source IDs (KeyError) or absent/unsupported official asset discovery (Unavailable).
    """
    if source == 'cellcall':
        return repo_assets('ShellyCoder/cellcall', lambda b: sorted(p for p in b if p.startswith('inst/extdata/new_ligand_receptor_TFs') and p.endswith('.txt')) + ['inst/extdata/KEGG_SYMBOL_ID.txt'],
                           lambda p: ('mouse', 'orthology-derived') if 'homology' in p else ('shared', 'unknown') if 'KEGG' in p else ('human', 'native'))
    if source == 'cellphonedb':
        return repo_assets('ventolab/cellphonedb-data', lambda b: sorted(p for p in b if p.startswith('data/') and p.endswith('_input.csv')))
    if source == 'cellchat':
        return repo_assets('jinworks/CellChat', lambda b: ['data/CellChatDB.human.rda', 'data/CellChatDB.mouse.rda'],
                           lambda p: ('mouse' if '.mouse.' in p else 'human', 'unknown'), prefer_release=False)
    if source == 'italk':
        return repo_assets('Coolgenome/iTALK', lambda b: ['data/LR_database.rda'])
    if source == 'celltalkdb':
        return repo_assets('ZJUFanLab/CellTalkDB', lambda b: ['database/human_lr_pair.rds', 'database/mouse_lr_pair.rds'] + sorted(p for p in b if p.startswith('data/') and any(s in p for s in ['ann_manual', 'gene2ensembl', 'gene_info', 'uniprot'])),
                           lambda p: ('mouse' if 'mouse_' in p else 'human', 'unknown'))
    if source == 'icellnet':
        return repo_assets('soumelis-lab/ICELLNET', lambda b: ['data/ICELLNETdb.tsv'], prefer_release=False)
    if source == 'dimitrov':
        return repo_assets('saezlab/liana-py', lambda b: [next(p for p in b if p.endswith('/resource/omni_resource.csv'))])
    if source == 'lrdb':
        selection, _ = repo_state('jcolinge/BulkSignalR', prefer_release=False)
        url = 'https://raw.githubusercontent.com/jcolinge/BulkSignalR/' + selection['commit'] + '/R/zzz.R'
        text, _ = page(url)
        host = re.search(r'url\s*<-\s*"([^"]+)"', text)
        path = re.search(r'urlLRdb\s*<-\s*paste0\(url,\s*"([^"]+)"', text)
        if not host or not path:
            raise Unavailable('BulkSignalR LRdb discovery code changed')
        selection['data_version'] = 'unversioned author endpoint; compare SHA-256'
        return selection, [asset(host[1] + path[1], headers=('ligand', 'receptor'))]
    if source == 'cellinker':
        url = SOURCES[source]['provider']
        try:
            text, final = page(url)
        except Unavailable as exc:
            if '416' not in str(exc):
                raise
            text, final = page(url + '?download=1')
        selected = [u for u in links(text, final) if any(x in u for x in ['Homo sapiens.txt', 'Mus musculus.txt', 'human-complex.csv', 'mouse-complex.csv'])]
        if len(selected) != 4:
            raise Unavailable('Expected both interaction and both complex links')
        return {'version': None, 'discovery_url': final}, [asset(u.replace(' ', '%20'), 'mouse' if 'Mus ' in u or 'mouse-' in u else 'human') for u in selected]
    if source == 'connectomedb':
        text, final = page(SOURCES[source]['provider'])
        index = next((u for u in links(text, final) if '/Current-Release/CSV/' in u), None)
        if not index:
            raise Unavailable('Current-Release CSV catalog missing')
        catalog, final = page(index)
        selected = [u for u in links(catalog, final) if re.search(r'_(human|mouse)\.csv$', u)]
        if len(selected) != 2:
            raise Unavailable('Current human/mouse CSV files missing')
        dates = re.findall(r'20\d\d-\d\d-\d\d', text)
        return {'version': 'Current-Release', 'catalog_dates': sorted(set(dates)), 'discovery_url': final}, [asset(u, 'mouse' if '_mouse' in u else 'human', 'orthology-derived' if '_mouse' in u else 'native') for u in selected]
    if source == 'ramilowski':
        text, final = page(SOURCES[source]['provider'])
        candidates = [u for u in links(text, final) if u.endswith('/PairsLigRec.txt')]
        if not candidates:
            raise Unavailable('PairsLigRec.txt missing from publication catalog')
        return {'version': 'April 2015 (static publication)'}, [asset(candidates[0])]
    if source in ('kirouac', 'pavlicev'):
        # Europe PMC distributes the original supplements as a ZIP; select only tables.
        from xml.etree import ElementTree
        pmc = 'PMC2990637' if source == 'kirouac' else 'PMC5340963'
        xml_url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmc + '/fullTextXML'
        root = ElementTree.fromstring(fetch(xml_url)[0])
        names = [x.get('{http://www.w3.org/1999/xlink}href') for x in root.iter('media')]
        names = [n for n in names if n and (n.endswith('.xls') if source == 'kirouac' else n.endswith('Supplemental_Tables.xlsx'))]
        if not names:
            raise Unavailable('Original supplemental table names absent')
        bundle = 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmc + '/supplementaryFiles'
        return {'version': '2010' if source == 'kirouac' else '2017', 'distribution': 'Europe PMC original publication supplements', 'discovery_url': xml_url}, [asset(bundle, name=n, archive_member=n) for n in names]
    if source == 'nichenet':
        selection, _ = repo_state('saeyslab/nichenetr', prefer_release=False)
        doc = 'https://raw.githubusercontent.com/saeyslab/nichenetr/' + selection['commit'] + '/vignettes/differential_nichenet.md'
        text, _ = page(doc)
        ids = re.findall(r'https://zenodo.org/record[s]?/(\d+)/files/lr_network', text)
        if not ids:
            raise Unavailable('Documented LR-network Zenodo record missing')
        record = get_json('https://zenodo.org/api/records/' + ids[0])
        latest = record.get('links', {}).get('latest')
        if latest:
            record = get_json(latest)
        selection.update(zenodo_record=record['id'], version=record['metadata'].get('version'), doi=record.get('doi'))
        selected = [f for f in record['files'] if f['key'].startswith('lr_network_') and any(s in f['key'] for s in ('human', 'mouse'))]
        if not any('human' in f['key'] for f in selected) or not any('mouse' in f['key'] for f in selected):
            raise Unavailable('Both species LR networks required')
        return selection, [asset(f['links']['self'], 'mouse' if 'mouse' in f['key'] else 'human', 'orthology-derived' if 'mouse' in f['key'] else 'unknown', name=f['key'], upstream_checksum=f['checksum'], md5=f['checksum'].removeprefix('md5:')) for f in selected]
    if source == 'omnipathppis':
        assets = []
        for taxon, species in [(9606, 'human'), (10090, 'mouse')]:
            query = {'datasets': 'ligrecextra', 'organisms': str(taxon), 'genesymbols': '1', 'fields': 'sources,references,ncbi_tax_id', 'format': 'tsv', 'license': 'academic'}
            assets.append(asset('https://omnipathdb.org/interactions?' + urlencode(query), species, 'orthology-derived' if species == 'mouse' else 'unknown', name=species + '/interactions.tsv', headers=('source', 'target'), query_parameters=query))
        for endpoint in ['intercell', 'complexes']:
            query = {'format': 'tsv', 'license': 'academic'}
            assets.append(asset('https://omnipathdb.org/' + endpoint + '?' + urlencode(query), 'human', 'unknown', name=endpoint + '.tsv', query_parameters=query))
        return {'version': None, 'service': 'https://omnipathdb.org', 'scope': 'ligrecextra plus intercellular roles and complex definitions; academic-license response'}, assets
    if source == 'gtopdb':
        page(SOURCES[source]['provider'])
        raise Unavailable('GtoPdb authenticated bulk discovery requires provider-approved access; adapter must be reviewed after login/API documentation is accessible')
    raise KeyError(source)
