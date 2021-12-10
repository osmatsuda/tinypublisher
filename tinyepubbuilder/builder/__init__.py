from dataclasses import dataclass
from pathlib import Path
from mako.template import Template # type: ignore
from typing import Union, Any, Generator
import datetime

import tinyepubbuilder as app
from tinyepubbuilder.package import PackageSpec, SpineItem

import logging
logger = logging.getLogger(f'{app.__appname__}.reader')


class BuildingError(Exception):
    def __init__(self, message: str):
        self.message = message

_BUILD_DIR_NAME_ = 'build'
    
class PackageBuilder():
    def __init__(self, pkgname: str) -> None:
        if pkgname.endswith('.epub'):
            pkgname = pkgname[:pkgname.index('.epub')]
        self.packagename = pkgname

    def build_with(self, spec: PackageSpec) -> None: # failable
        self.make_package_dirs(spec.curdir)
        self.make_package_document(spec)
        self.make_navigation_xhtml(spec)

    def make_package_dirs(self, curdir: Path) -> None: # failable
        self.curdir = curdir
        builddir = _make_build_dir(curdir, _BUILD_DIR_NAME_, _BUILD_DIR_NAME_+'.'+app.__appname__)
        destdir = builddir / self.packagename
        destdir.mkdir(exist_ok=True)
        (destdir / 'META-INF').mkdir(exist_ok=True)
        (destdir / 'book/items').mkdir(parents=True, exist_ok=True)
        self.destdir = destdir
        self.package_doc = destdir / 'book/package.opf'

        mimetype = destdir / 'mimetype'
        mimetype.touch()
        with open(mimetype, 'w') as f:
            f.write('application/epub+zip')

        container_file = destdir / 'META-INF/container.xml'
        container_file.touch()
        _make_container_file(container_file, self.package_doc)

    def make_package_document(self, spec: PackageSpec) -> None:
        pkg_doc_spec: dict[str, Any] = _make_pkg_doc_spec(spec, self.destdir.name)
        pkg_doc_spec['pkg_items'] = _make_pkg_doc_items(spec.spine, self.curdir.resolve())
        template = _template(self.package_doc.name)

        with open(self.package_doc, 'w') as f:
            f.write(template.render(**pkg_doc_spec))

    def make_navigation_xhtml(self, spec: PackageSpec) -> None:
        pass

    def zipup(self) -> None:
        pass


# Package document

@dataclass(frozen=True)
class _ManifestItem:
    id: str
    href: str
    media_type: str
    spine_item: bool = False
    def __hash__(self):
        return hash(self.href)
    def __eq__(self, other):
        return self.href == other.href

def _make_pkg_doc_spec(spec: PackageSpec, pkg_name: str) -> dict[str,str]:#Union[str, list[_ManifestItem]]]:
    d = dict()
    d['id'] = spec.id

    title = spec.book_title
    if not title:
        title = pkg_name
    d['book_title'] = title

    ltag = spec.language_tag
    if ltag == 'und':
        logger.warning(f'''{app.__appname__} failed to specify the language-tag.
  You should fill manually "<dc:language>und</dc:language>" in the package document
  -- "<build-dir>/{pkg_name}/book/package.opf".''')
    d['language_tag'] = ltag

    d['modified_date'] = datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z'

    return d

def counter() -> Generator:
    i = 0
    while True:
        yield i+1
        i += 1
        
def _make_pkg_doc_items(spine: list[SpineItem], curdir: Path) -> list[_ManifestItem]:
    c = counter()
    items = set()
    for spine_item in spine:
        doc_path = Path(spine_item.content_document)
        item = _ManifestItem(
            id = f'item{next(c)}',
            href = str(doc_path.relative_to(curdir)),
            media_type = spine_item.media_type,
            spine_item = True,
        )
        items.add(item)
        if not spine_item.content_includes:
            continue
        for uri, mime in spine_item.content_includes:
            item = _ManifestItem(
                id = f'item{next(c)}',
                href = str(Path(uri).relative_to(curdir)),
                media_type = mime,
            )
            items.add(item)
    c.close()
    return list(items)


# Package directory utils

def _template(name: str) -> Template:
    filename = str(Path(__file__).parent / 'templates' / name)
    return Template(filename=filename)
    
def _make_build_dir(stem: Path, *candidates: str) -> Path: # failable
    assert len(candidates) > 0
    
    dest = stem / candidates[0]
    dotfile = dest / ('.' + app.__appname__)
    if not dest.exists():
        dest.mkdir(0o755)
        dotfile.touch(0o644)
        logger.info(f'making a build dir: {dest.resolve()}')
        return dest
    if dotfile.exists():
        return dest
    if len(candidates) > 1:
        return _make_build_dir(stem, *candidates[1:])

    logger.warning(f'A build dir should have a file "{dotfile.name}".')
    raise BuildingError(f'{app.__appname__} cannot make a build dir: {dest.resolve()}')

def _make_container_file(path: Path, pkg_doc: Path) -> None:
    pkg_doc_loc = str(pkg_doc.relative_to(path.parent.parent))
    template = _template(path.name)
    with open(path, 'w') as f:
        f.write(template.render(pkg_doc_loc=pkg_doc_loc))
        
    
