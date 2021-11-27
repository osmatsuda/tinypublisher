from dataclasses import dataclass, field
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
    index_title: str
    content_caption: str
    content_size: Optional[tuple[int, int]] = None
    content_includes: Optional[list[str]] = None


@dataclass
class PackageSpec:
    spine: list[SpineItem] = field(default_factory=list)
    
    def append_spine_item(self, **dargs) -> None:
        items = {k: dargs[k] for k in SpineItem.__dataclass_fields__ if dargs.__contains__(k)} # type: ignore
        self.spine.append(SpineItem(**items))


