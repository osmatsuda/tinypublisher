from dataclasses import dataclass, field
from enum import Enum
from argparse import Namespace
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_DNS
from typing import Optional
import os, magic


class MediaType(Enum):
    GIF = 'image/gif'
    JPG = 'image/jpeg'
    PNG = 'image/png'
    SVG = 'image/svg+xml'
    XHTML = 'application/xhtml+xml'
    CSS = 'text/css'
    JS = 'application/javascript'

    @classmethod
    def contain(cls, target: str) -> bool:
        for entry in cls:
            if target == entry.value:
                return True
        return False

    @classmethod
    def predict_content_document(cls, target: str) -> bool:
        return target == cls.SVG.value or target == cls.XHTML.value

    @classmethod
    def predict_text(cls, target: str) -> bool:
        return target in _TEXTTYPE

_TEXTTYPE = {
    MediaType.SVG.value,
    MediaType.XHTML.value,
    MediaType.CSS.value,
    MediaType.JS.value,
}


@dataclass
class SpineItem:
    content_document: str
    media_type: str
    index_title: str
    content_title: str
    content_caption: str
    content_lang: Optional[str] = None
    content_size: Optional[tuple[int, int]] = None
    content_includes: Optional[list[tuple[str,str]]] = None


    
@dataclass
class PackageSpec:
    curdir: Path
    spine: list[SpineItem] = field(default_factory=list)
    # if not book_title then build/<dest-name> is used
    book_title: str = ''
    author: Optional[str] = None
    _cover_image: Optional[Path] = None
    _language_tag: Optional[str] = None
    _id: Optional[str] = None
    _uuid: str = ''
    
    def append_spine_item(self, **dargs) -> None:
        items = {k: dargs[k] for k in SpineItem.__dataclass_fields__ if dargs.__contains__(k)} # type: ignore
        self.spine.append(SpineItem(**items))

    @property
    def cover_image(self) -> Optional[Path]:
        return self._cover_image
    @cover_image.setter
    def cover_image(self, src: Optional[str]):
        path = None
        if src:
            path = Path(src)
            if not path.is_file():
                raise PackageError(f'"{src}" does not exist')

            mime = magic.from_file(str(path), mime=True)
            if not MediaType.contain(mime):
                raise PackageError(f'The file type of "{path}" is not supported.')

        self._cover_image = path

    @property
    def language_tag(self) -> str:
        if self._language_tag is None:
            return "und"
        return self._language_tag
    @language_tag.setter
    def language_tag(self, tag: Optional[str]):
        if tag is None:
            lng = self.find_from_spine_item('content_lang')
            if lng is None:
                lng = os.environ.get('LANG')
                if lng:
                    lng = lng.split('.')[0]
                    lng = lng.split('_')[0]
            if not lng:
                lng = 'und'
            self._language_tag = lng
        else:
            self._language_tag = tag

    @property
    def id(self) -> str:
        if self._id is None:
            return self.uuid
        return self._id
    @id.setter
    def id(self, _id: Optional[str]):
        self._id = _id
        
    @property
    def uuid(self) -> str:
        return self._uuid
    @uuid.setter
    def uuid(self, dns: Optional[str]):
        if dns is None:
            self._uuid = uuid4().urn
        else:
            self._uuid = uuid5(NAMESPACE_DNS, dns).urn

    def find_from_spine_item(self, attr: str) -> Optional[str]:
        for item in self.spine:
            if attr in set(item.__dataclass_fields__.keys()): # type: ignore
                finded = item.__getattribute__(attr)
                if finded:
                    return finded
        return None

    
class PackageError(Exception):
    def __init__(self, message):
        super().__init__(message)


