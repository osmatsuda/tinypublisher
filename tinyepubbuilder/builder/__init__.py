from dataclasses import dataclass
from pathlib import Path
from mako.template import Template # type: ignore
from typing import Union, Any, Generator, Optional
import datetime

import tinyepubbuilder as app
from tinyepubbuilder.package import PackageSpec, SpineItem, MediaType

import logging
logger = logging.getLogger(f'{app.__appname__}.builder')


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
        self.make_navigation_document(spec)
        self.package_content_items(spec)

    def make_package_dirs(self, curdir: Path) -> None: # failable
        self.curdir = curdir
        builddir = _make_build_dir(curdir, _BUILD_DIR_NAME_, _BUILD_DIR_NAME_+'.'+app.__appname__)
        destdir = builddir / self.packagename
        destdir.mkdir(exist_ok=True)
        (destdir / 'META-INF').mkdir(exist_ok=True)
        (destdir / 'book/items').mkdir(parents=True, exist_ok=True)
        self.destdir = destdir

        mimetype = destdir / 'mimetype'
        mimetype.touch()
        with open(mimetype, 'w') as f:
            f.write('application/epub+zip')

        container_file = destdir / 'META-INF/container.xml'
        pkg_opf = destdir / 'book/package.opf'
        container_file.touch()
        _make_container_file(container_file, pkg_opf)

    def make_package_document(self, spec: PackageSpec) -> None:
        assert self.destdir is not None
        
        pkg_doc_spec: dict[str, Any] = _make_pkg_doc_spec(spec, self.destdir.name)
        pkg_doc_spec['pkg_items'] = _make_pkg_doc_items(spec.spine, self.curdir.resolve())
        self.package_document_spec = pkg_doc_spec

        pkg_opf = self.destdir / 'book/package.opf'
        template = _template(pkg_opf.name)
        with open(pkg_opf, 'w') as f:
            logger.info(f'making a Package Document\n  -- {str(pkg_opf)}')
            f.write(template.render(**pkg_doc_spec))

    def make_navigation_document(self, spec: PackageSpec) -> None:
        if self.__dict__.get('package_document_spec') is None:
            self.make_package_document(spec)

        nav_xhtml = self.destdir / 'book/navigation.xhtml'
        template = _template(nav_xhtml.name)
        with open(nav_xhtml, 'w') as f:
            logger.info(f'making a Navigation Document\n  -- {str(nav_xhtml)}')
            f.write(template.render(**self.package_document_spec))

    def package_content_items(self, spec: PackageSpec) -> None:
        pass
    
    def zipup(self) -> None:
        pass

    
# Package document

@dataclass(frozen=True)
class _ManifestItem:
    id: str
    href: str
    media_type: str
    title: Optional[str] = None
    spine_item: bool = False
    def __hash__(self):
        return hash(self.href)
    def __eq__(self, other):
        return self.href == other.href

def _make_pkg_doc_spec(spec: PackageSpec, pkg_name: str) -> dict[str,str]:
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
        href = str(doc_path.relative_to(curdir))
        if (spine_item.media_type == MediaType.XHTML.value or
            (spine_item.media_type == MediaType.SVG.value and not spine_item.content_caption)):
            items.add(_ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + href,
                title = spine_item.index_title,
                media_type = spine_item.media_type,
                spine_item = True,
            ))
        else:
            item = _ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + href,
                title = spine_item.index_title,
                media_type = spine_item.media_type,
            )
            items.add(item)
            items.add(_wrapped_xhtml(item, f'item{next(c)}'))

    for spine_item in spine:
        if not spine_item.content_includes:
            continue
        for uri, mime in spine_item.content_includes:
            items.add(_ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + str(Path(uri).relative_to(curdir)),
                media_type = mime,
            ))
    c.close()
    return sorted(items, key=lambda itm: int(itm.id[4:]))

def _wrapped_xhtml(item: _ManifestItem, id: str) -> _ManifestItem:
    return _ManifestItem(
        id = id,
        href = item.href + '.xhtml',
        title = item.title,
        media_type = MediaType.XHTML.value,
        spine_item = True,
    )


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
        
    
