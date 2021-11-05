import io, csv, pathlib
import magic, mimetypes
from dataclasses import dataclass
from typing import Optional

from tinyepubbuilder.package import PackageSpec, SUPPORTED_MEDIA_TYPES

@dataclass
class _State:
    row: int
    col: int
    def succ_row(self):
        self.row += 1
        self.col = 0
    def succ_col(self):
        self.col += 1

_Spec = dict[str, Optional[str]]

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

    def parseEntry(self, entry: list[str], state: _State) -> _Spec:
        spec = _Spec()
        
        spec['content_document'] = entry[state.col]
        spec |= _check_file_type(content_document, state)

        state.succ_col()
        spec['index_title'] = entry[state.col] if len(entry) > state.col else None

        state.succ_col()
        spec['content_caption'] = entry[state.col] if len(entry) > state.col else None

        return spec


class ReaderError(Exception):
    def __init__(self, message: str, state: _State):
        self.message = message + f' pos: {state.row},{state.col}'
        

def _check_file_type(path: str, state: _State) -> _Spec:
    if not pathlib.Path(content_document).is_file():
        raise ReaderError(f'{content_document} should points a regular file.', state)

    mgc = magic.Magic(mime=True)
    mime = mgc.from_file(path)
    if mime == 'text/xml':
        mime, _ = mimetypes.guess_type(path)
        
    if mime not in SUPPORTED_MEDIA_TYPES:
        raise ReaderError(f'The file type of {content_document} is not supported.', state)

    return _Spec({'mimetype': mime})
    
