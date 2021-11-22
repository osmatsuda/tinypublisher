from dataclasses import dataclass
from argparse import Namespace
from typing import Optional


SUPPORTED_CONTENT_MEDIA_TYPES = {
    'image/gif',
    'image/jpeg',
    'image/png',
    'image/svg+xml',
    'application/xhtml+xml',
}


@dataclass
class SpineItem:
    content_document: str
    media_type: str
    index_title: Optional[str] = None
    content_caption: Optional[str] = None
    content_size: Optional[tuple[int, int]] = None
    content_linked: Optional[list[str]] = None

class PackageSpec:
    def append_spine_item(self, **dict_args) -> None:
        pass
    
    def add_spec(self, name: str, args: Namespace) -> None: #failable
        pass


