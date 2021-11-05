from dataclasses import dataclass
from argparse import Namespace
from typing import Optional


SUPPORTED_MEDIA_TYPES = {
    'image/gif',
    'image/jpeg',
    'image/png',
    'image/svg+xml',
    'text/css',
    'application/xhtml+xml',
    'application/javascript',
    'text/javascript'
}

@dataclass
class _SpineItem:
    content_document: str
    index_title: Optional[str] = None
    content_caption: Optional[str] = None
    
class PackageSpec:
    def append_spine_item(self, **dict_args) -> None:
        pass
    
    def add_spec(self, name: str, args: Namespace) -> None: #failable
        pass


