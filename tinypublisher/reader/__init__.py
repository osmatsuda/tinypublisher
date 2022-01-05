import io, csv, mimetypes, re
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any, Iterable
import magic

import tinypublisher as app
from tinypublisher.package import PackageSpec, MediaType

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

_SpineItem = dict[str, Any]


class FileListParser:
    def __init__(self, curdir='.'):
        self.curdir = Path(curdir)

    def parse(self, fileobj: io.TextIOBase) -> PackageSpec:
        lines = csv.reader(fileobj, delimiter="\t")
        spec = PackageSpec(curdir=self.curdir)
        s = _State(0, 0)
        for entry in lines:
            if entry:
                spine_item = self.parseEntry(entry, s)
                spec.append_spine_item(**spine_item)
                s.succ_row()
        return spec
    
    def parse_text(self, text: str) -> PackageSpec:
        return self.parse(io.StringIO(text))

    def parseEntry(self, entry: list[str], state: _State) -> _SpineItem:
        spine_item: _SpineItem = {}

        path = (self.curdir / entry[state.col]).resolve()
        spine_item['content_document'] = str(path)
        spine_item |= _check_file_type(path, state)

        state.succ_col()
        index_title = entry[state.col] if len(entry) > state.col else ''
        if index_title == '-':
            if spine_item.__contains__('content_title'):
                index_title = spine_item['content_title']
            else:
                index_title = path.name
                spine_item['content_title'] = index_title
        spine_item['index_title'] = index_title
        if not spine_item.__contains__('content_title'):
            spine_item['content_title'] = ''

        state.succ_col()
        content_caption = entry[state.col] if len(entry) > state.col else ''
        if content_caption == '-' and spine_item.__contains__('content_title'):
            content_caption = spine_item['content_title']
        spine_item['content_caption'] = content_caption

        return spine_item

    

class BaseError(app.AppBaseError):
    def __init__(self, message: str, state: str):
        self.message = f'{message} [{state}]'
        
class ReaderError(BaseError):
    def __init__(self, message: str, state: _State):
        super().__init__(message, f'pos: {state.row},{state.col}')

        
        
def _check_file_type(path: Path, state: _State) -> _SpineItem:
    if not path.is_file():
        raise ReaderError(f'"{path}" is nonexist or not a regular file.', state)

    mime = magic.from_file(str(path), mime=True)
    if mime == 'text/xml':
        mime, _ = mimetypes.guess_type(path)
        
    if not MediaType.contain(mime):
        raise ReaderError(f'The file type of "{path}" is not supported.', state)

    spine_item = _SpineItem({'media_type': mime}) 

    if MediaType.predict_content_document(mime):
        spine_item |= _check_content_document(path, mime)

    if mime.startswith('image/'):
        spine_item |= _image_size(magic.from_file(str(path)))

    return spine_item

def _image_size(spec: Optional[str]) -> _SpineItem:
    spine_item: _SpineItem = {}
    if not spec:
        return spine_item

    r = re.compile('\s*(\d+)\s*x\s*(\d+)\s*')
    for c in spec.split(','):
        m = r.match(c)
        if m:
            spine_item['content_size'] = (int(m.group(1)), int(m.group(2)))
    return spine_item
        


class ContentDocumentError(Exception):
    def __init__(self, message: str, state):
        super().__init__(message, f'line: {state.row}')

def _check_content_document(path: Path, mime: str) -> _SpineItem:
    logger.info(f'checking "{path.name}"')

    tree = ET.parse(path)
    root = tree.getroot()
    links = []
    title = root.find('.//{*}title')

    if mime.endswith('xhtml+xml'):
        links = _find_linked_in_xhtml(root)
    elif mime.endswith('svg+xml'):
        links = _find_linked_in_svg(root)

    validated_links = _validated_links(links, path)
    spine_item = _SpineItem({'content_includes': validated_links}) if validated_links else {}
    if title is not None and title.text:
        spine_item['content_title'] = title.text.strip()
    else:
        content_text = _content_document_text(root)
        if content_text:
            spine_item['content_title'] = content_text

    for key in root.attrib:
        if key.endswith('lang'):
            spine_item['content_lang'] = root.get(key)
            break
    return spine_item

def _content_document_text(root: ET.Element) -> str:
    if root.tag.endswith('svg'):
        txt_or_tspn = lambda e: e.tag.endswith('text') or e.tag.endswith('tspan')
        return _content_text(filter(txt_or_tspn, root.findall('.//*')))
    elif root.tag.endswith('html'):
        return _content_text(root.findall('.//{*}body//*'))
    return ''

def _content_text(elements: Iterable) -> str:
    text = ''
    for elm in elements:
        if elm.text:
            words = ' '.join(elm.text.split())
            if words:
                text += ' ' + words
    text = text.strip()
    if len(text) > 20:
        return text[:20] + '…'
    return text


def _validated_links(uris: list[str], current: Path) -> list[tuple[str,str]]:
    re_invalid = re.compile(f'^(?:https?|mailto|urn):|({current.name})?#')
    re_foreign = re.compile('^https?:')
    links = set()

    for uri in uris:
        if re_invalid.search(uri):
            if re_foreign.search(uri):
                logger.warning(f'''"{current}" contains a foreign resource
  -- {uri},
  {app.__appname__} doesn't treat this.''')
            continue
        
        path = current.parent.joinpath(uri).resolve()
        if not path.is_file():
            logger.warning(f'''"{current}" references to a nonexistant local file
  -- {uri}.''')
            continue

        mime = magic.from_file(str(path), mime=True)
        if mime in {'text/xml', 'text/plain'}:
            mime, _ = mimetypes.guess_type(path)

        links.add((str(path.absolute()), mime))

        additionals: list[tuple[str,str]] = []
        if MediaType.predict_content_document(mime):
            spine = _check_content_document(path, mime)
            if spine.__contains__('content_includes'):
                additionals = spine['content_includes']
        elif mime == 'text/css':
            additionals = _find_linked_in_css(path)

        if additionals:
            links = links | set(additionals)

    return list(links)

def _find_linked_in_css(path: Path) -> list[tuple[str,str]]:
    re_url = re.compile('url\([\'"]?([^\("\']+)[\'"]?\)')
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
            if elm.attrib.__contains__('href'):
                ref = elm.attrib['href']
        elif re_src.match(elm.tag):
            if elm.attrib.__contains__('src'):
                ref = elm.attrib['src']
        elif re_data.match(elm.tag):
            if elm.attrib.__contains__('data'):
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

    
