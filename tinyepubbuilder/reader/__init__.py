import io, csv, mimetypes, re
from pathlib import Path
import xml.etree.ElementTree as ET
import magic

from dataclasses import dataclass
from typing import Optional, Any

from tinyepubbuilder.package import PackageSpec, SUPPORTED_CONTENT_MEDIA_TYPES

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
    tree = ET.parse(doc_path)
    root = tree.getroot()
    if mime.endswith('xhtml+xml'):
        _paths = _find_linked_in_xhtml(root)
    elif mime.endswith('svg+xml'):
        _paths = _find_linked_in_svg(root)
    else:
        _paths = []

    current = Path(doc_path)
    re_invalid = re.compile(f'^(?:http|mailto|urn):|({current.name})?#')
    paths = []
    for p in _paths:
        if re_invalid.search(p):
            # warn foreign resource
            continue
        pp = current.parent.joinpath(p).resolve()
        if not pp.is_file():
            # warn p doesn't exist
            continue

        paths.append(p)
        p_mime = magic.from_file(str(pp), mime=True)
        if p_mime == 'text/xml':
            p_mime, _ = mimetypes.guess_type(pp)
        if p_mime in CONTENT_DOCUMENT_MEDIA_TYPES:
            rp = _check_content_document(str(pp), p_mime)
            if rp:
                paths.append(rp)

    return _Spine({'content_linked': paths}) if paths else {}

def _find_linked_in_xhtml(root: ET.Element) -> list[str]:
    re_href = re.compile('\{.+\}link')
    re_src = re.compile('\{.+\}(?:script|img|embed|iframe|source)')
    re_data = re.compile('\{.+\}object')
    paths = []
    for elm in root.findall('.//*'):
        ref = ''
        if re_href.match(elm.tag):
            if elm.attrib.get('rel').find('stylesheet') < 0:
                continue
            ref = elm.attrib.get('href')
        elif re_src.match(elm.tag):
            ref = elm.attrib.get('src')
        elif re_data.match(elm.tag):
            ref = elm.attrib.get('data')

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
