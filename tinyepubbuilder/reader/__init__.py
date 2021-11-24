import io, csv, mimetypes, re
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any
import magic

import tinyepubbuilder as app
from tinyepubbuilder.package import PackageSpec, SUPPORTED_CONTENT_MEDIA_TYPES

import logging
logger = logging.getLogger(f'{app.__appname__}.reader')


@dataclass
class _State:
    row: int
    col: int
    def succ_row(self):
        self.row += 1
        self.col = 0
    def succ_col(self):
        self.col += 1

_Spine = dict[str, Any]

class FileListParser:
    def __init__(self):
        self.status = None

    def parse(self, fileobj: io.TextIOBase) -> PackageSpec:
        lines = csv.reader(fileobj, delimiter="\t")
        spec = PackageSpec()
        s = _State(0, 0)
        for entry in lines:
            if entry:
                spine = self.parseEntry(entry, s)
                spec.append_spine_item(**spine)
                s.succ_row()
        return spec
    
    def parse_text(self, text: str) -> PackageSpec:
        return self.parse(io.StringIO(text))

    def parseEntry(self, entry: list[str], state: _State) -> _Spine:
        spine: _Spine = {}

        path = entry[state.col]
        spine['content_document'] = path
        spine |= _check_file_type(path, state)

        state.succ_col()
        spine['index_title'] = entry[state.col] if len(entry) > state.col else ''

        state.succ_col()
        spine['content_caption'] = entry[state.col] if len(entry) > state.col else ''

        return spine


class BaseError(Exception):
    def __init__(self, message: str, state: str):
        self.message = f'{message} [{state}]'
        
class ReaderError(BaseError):
    def __init__(self, message: str, state: _State):
        super().__init__(message, f'pos: {state.row},{state.col}')

        
CONTENT_DOCUMENT_MEDIA_TYPES = set(['image/svg+xml', 'application/xhtml+xml'])
        
def _check_file_type(path: str, state: _State) -> _Spine:
    if not Path(path).is_file():
        raise ReaderError(f'{path} should points a regular file.', state)

    mime = magic.from_file(path, mime=True)
    if mime == 'text/xml':
        mime, _ = mimetypes.guess_type(path)
        
    if mime not in SUPPORTED_CONTENT_MEDIA_TYPES:
        raise ReaderError(f'The file type of {path} is not supported.', state)

    spine = _Spine({'media_type': mime}) 

    if mime in CONTENT_DOCUMENT_MEDIA_TYPES:
        spine |= _check_content_document(path, mime)

    if mime.startswith('image/'):
        spine |= _image_size(magic.from_file(path))

    return spine

def _image_size(spec: Optional[str]) -> _Spine:
    spine: _Spine = {}
    if not spec:
        return spine

    r = re.compile('\s*(\d+)\s*x\s*(\d+)\s*')
    for c in spec.split(','):
        m = r.match(c)
        if m:
            spine['content-size'] = (int(m.group(1)), int(m.group(2)))
    return spine
        

class ContentDocumentError(Exception):
    def __init__(self, message: str, state):
        super().__init__(message, f'line: {state.row}')

def _check_content_document(doc_path: str, mime: str) -> _Spine:
    logger.info(f'checking "{doc_path}"')

    tree = ET.parse(doc_path)
    root = tree.getroot()
    links = []
    if mime.endswith('xhtml+xml'):
        linkes = _find_linked_in_xhtml(root)
    elif mime.endswith('svg+xml'):
        links = _find_linked_in_svg(root)

    links = _validated_links(linkes, Path(doc_path))
    return _Spine({'content_linked': links}) if links else {}


def _validated_links(uris: list[str], current: Path) -> list[str]:
    re_invalid = re.compile(f'^(?:https?|mailto|urn):|({current.name})?#')
    re_foreign = re.compile('^https?:')
    links = set()
    for uri in uris:
        if re_invalid.search(uri):
            if re_foreign.search(uri):
                logger.warn(f'''"{current}" contains a foreign resource ({uri})
  {app.__appname__} doesn't treat this''')
            continue
        path = current.parent.joinpath(uri).resolve()
        if not path.is_file():
            logger.warn(f'"{current}" containts a nonexistant link ({uri})')
            continue

        links.add(str(path.absolute()))
        additionals: list[str] = []
        mime = magic.from_file(str(path), mime=True)
        if mime in {'text/xml', 'text/plain'}:
            mime, _ = mimetypes.guess_type(path)
        if mime in CONTENT_DOCUMENT_MEDIA_TYPES:
            spine = _check_content_document(str(path), mime)
            if spine.__contains__('content_linked'):
                additionals = spine['content_linked']
        elif mime == 'text/css':
            additionals = _find_linked_in_css(path)
        if additionals:
            links = links | set(additionals)

    return list(links)

def _find_linked_in_css(path: Path) -> list[str]:
    re_url = re.compile('url\("?([^\("]+)"?\)')
    links = set()
    with open(path) as f:
        for line in f:
            links |= set(re_url.findall(line))

    return _validated_links(list(links), path)
    
def _find_linked_in_xhtml(root: ET.Element) -> list[str]:
    re_href = re.compile('\{.+\}link')
    re_src = re.compile('\{.+\}(?:script|img|embed|iframe|source)')
    re_data = re.compile('\{.+\}object')
    paths = []
    for elm in root.findall('.//*'):
        ref = ''
        if re_href.match(elm.tag):
            rel = elm.attrib.get('rel')
            if rel and rel.find('stylesheet') < 0:
                continue
            if elm.__contains__('href'):
                ref = elm.attrib['href']
        elif re_src.match(elm.tag):
            if elm.__contains__('src'):
                ref = elm.attrib['src']
        elif re_data.match(elm.tag):
            if elm.__contains__('data'):
                ref = elm.attrib['data']

        if ref:
            paths.append(ref)
    return paths

def _find_linked_in_svg(root: ET.Element) -> list[str]:
    paths = []
    for elm in root.findall('.//*[@{http://www.w3.org/1999/xlink}href]'):
        ref = elm.attrib.get('{http://www.w3.org/1999/xlink}href')
        if ref:
            paths.append(ref)
    return paths

