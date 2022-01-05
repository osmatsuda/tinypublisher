from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
from mako.template import Template # type: ignore
from typing import Union, Any, Generator, Optional
import datetime, magic, urllib.parse

import tinypublisher as app
from tinypublisher.package import PackageSpec, SpineItem, MediaType

import logging
logger = logging.getLogger(f'{app.__appname__}.builder')


class BuilderError(app.AppBaseError):
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
        if spec.cover_image:
            _pkg_doc_add_cover_image(spec.cover_image, pkg_doc_spec, self.curdir)
        self.package_document_spec = pkg_doc_spec

        pkg_opf = self.destdir / 'book/package.opf'
        template = _template(pkg_opf.name)

        logger.info(f'making a Package Document\n  -- {str(pkg_opf)}')
        with open(pkg_opf, 'w') as f:
            f.write(template.render(**self.package_document_spec))

    def make_navigation_document(self, spec: PackageSpec) -> None:
        if self.__dict__.get('package_document_spec') is None:
            self.make_package_document(spec)

        nav_xhtml = self.destdir / 'book/navigation.xhtml'
        template = _template(nav_xhtml.name)

        logger.info(f'making a Navigation Document\n  -- {str(nav_xhtml)}')
        with open(nav_xhtml, 'w') as f:
            f.write(template.render(**self.package_document_spec))

    def package_content_items(self, spec: PackageSpec) -> None:
        if self.__dict__.get('package_document_spec') is None:
            self.make_package_document(spec)

        for item in self.package_document_spec['pkg_items']:
            target = self.destdir / 'book' / item.href
            if item.spine_item_p and item.src_path is None:
                _make_wrapping_doc(spec, item, target)
            else:
                _copy_item(item, target)
    
    def zipup(self) -> None:
        zt = self.destdir.parent / (self.packagename + '.epub')
        logger.info(f'making a EPUB package\n  -- {str(zt)}')
        with ZipFile(zt, 'w') as zf:
            _zipwrite(zf, self.destdir, *self.destdir.iterdir())


            
# zipup

def _zipwrite(zf: ZipFile, base: Path, *paths: Path) -> None:
    for p in paths:
        if p.is_file():
            zf.write(p, str(p.relative_to(base)), ZIP_DEFLATED)
        elif p.is_dir():
            zf.write(p, str(p.relative_to(base)))
            _zipwrite(zf, base, *p.iterdir())


            
# Packaging documents

@dataclass
class _WrappingDocSpec:
    language_tag: str
    title: str
    caption: str
    content_src: str
    css_href: str = ''
    svg: str = ''

def _src_loc(uri: str, curdir: Path) -> str:
    base = curdir.resolve()
    dest = Path(uri)
    while not dest.is_relative_to(base):
        base = base.parent
    return str(dest.relative_to(base))

def _wrapping_doc_spec(item_href: str, spec: PackageSpec) -> _WrappingDocSpec:
    loc = item_href[len('items/'):]
    loc = loc[:-len('.xhtml')]
    for spine_item in spec.spine:
        if _src_loc(spine_item.content_document, spec.curdir) == loc:
            break
    return _WrappingDocSpec(
        language_tag = spec.language_tag,
        title = spine_item.index_title if spine_item.index_title else spine_item.content_title,
        caption = spine_item.content_caption,
        content_src = loc,
        svg = spine_item.content_document if spine_item.media_type == MediaType.SVG.value else '',
    )

_CSS_HREF = None
def _css_href(spine: list[SpineItem]) -> str:
    global _CSS_HREF
    if _CSS_HREF is None:
        c = counter()
        stop = False
        while not stop:
            href = f'{app.__appname__}G{next(c)}'
            stop = True
            for item in spine:
                if not item.content_includes:
                    continue
                for uri, _ in item.content_includes:
                    if Path(uri).name == href + '.css':
                        stop = False
                        break
                if not stop:
                    break
        _CSS_HREF = href + '.css'
        c.close()
    return _CSS_HREF

def _svg_content(src: str) -> str:
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    svg = ET.parse(src)
    svg_content = ET.tostring(svg.getroot(), encoding='unicode')
    return svg_content.replace('\n', '\n      ')
    
def _make_wrapping_doc(spec: PackageSpec, item: _ManifestItem, target: Path) -> None:
    item_spec = asdict(_wrapping_doc_spec(item.href, spec))
    css_name = _css_href(spec.spine)
    item_spec['css_href'] = css_name
    if item_spec['svg']:
        item_spec['svg'] = _svg_content(item_spec['svg'])
    
    template = _template('page.xhtml')

    logger.info(f'making a page\n  -- {str(target)}')
    if not target.parent.is_dir():
        target.parent.mkdir(parents=True)
    with open(target, 'w') as f:
        f.write(template.render(**item_spec))

    css_template = Path(__file__).parent / 'templates/page.css'
    (target.parent / css_name).write_text(css_template.read_text())
    
def _copy_item(src_item: _ManifestItem, target: Path) -> None:
    src = src_item.src_path
    if src is None: return

    src_loc = src_item.href[len('items/'):]
    logger.info(f'copying "{src_loc}" to\n  -- {str(target)}')
    if not target.parent.is_dir():
        target.parent.mkdir(parents=True)
    if MediaType.predict_text(src_item.media_type):
        target.write_text(src.read_text())
    else:
        target.write_bytes(src.read_bytes())


    
# Package document

@dataclass
class _ManifestItem:
    id: str
    href: str
    media_type: str
    src_path: Optional[Path] = None
    index_title: Optional[str] = None
    content_title: Optional[str] = None
    spine_item_p: bool = False
    cover_image_p: bool = False
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

    if spec.author:
        d['author'] = spec.author

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
    index_title_count = 0
    for spine_item in spine:
        doc_path = Path(spine_item.content_document)
        if not doc_path.is_relative_to(curdir):
            raise BuilderError(f'''All resouces should be in the descendant of the current directory.
  -- {str(doc_path)}
  -- curdir: {str(curdir)}''')
        
        href = str(doc_path.relative_to(curdir))
        
        if (spine_item.media_type == MediaType.XHTML.value or
            (spine_item.media_type == MediaType.SVG.value and not spine_item.content_caption)):
            items.add(_ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + href,
                index_title = spine_item.index_title,
                media_type = spine_item.media_type,
                spine_item_p = True,
                src_path = Path(spine_item.content_document),
            ))
        else:
            if spine_item.media_type != MediaType.SVG.value:
                items.add(_ManifestItem(
                    id = f'item{next(c)}',
                    href = 'items/' + href,
                    media_type = spine_item.media_type,
                    src_path = Path(spine_item.content_document),
                ))
            items.add(_wrapping_doc(_ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + href,
                index_title = spine_item.index_title,
                content_title = spine_item.content_title,
                media_type = spine_item.media_type,
                src_path = Path(spine_item.content_document),
            ), f'item{next(c)}'))
        if spine_item.index_title:
           index_title_count += 1

    if not index_title_count:
        for item in items:
            if not item.spine_item_p:
                continue
            if item.content_title:
                item.index_title = item.content_title
            elif item.src_path:
                item.index_title = item.src_path.stem
            else:
                basename = Path(item.href).stem
                if basename[basename.rfind('.'):] == '.svg':
                    basename = basename[:basename.rfind('.')]
                item.index_title = basename

    for spine_item in spine:
        if not spine_item.content_includes:
            continue
        for uri, mime in spine_item.content_includes:
            uri_path = Path(uri)
            if not uri_path.is_relative_to(curdir):
                raise BuilderError(f'''All resouces should be in the descendant of the current directory.
  -- {str(uri_path)}
  -- curdir: {str(curdir)}''')

            items.add(_ManifestItem(
                id = f'item{next(c)}',
                href = 'items/' + str(uri_path.relative_to(curdir)),
                media_type = mime,
                src_path = Path(uri),
            ))
    c.close()
    return sorted(items, key=lambda itm: int(itm.id[4:]))

def _wrapping_doc(item: _ManifestItem, id: str) -> _ManifestItem:
    return _ManifestItem(
        id = id,
        href = item.href + '.xhtml',
        index_title = item.index_title,
        content_title = item.content_title,
        media_type = MediaType.XHTML.value,
        spine_item_p = True,
    )

def _pkg_doc_add_cover_image(img_path: Path, manifest: dict[str, Any], curdir: Path) -> None:
    find = False
    for item in manifest['pkg_items']:
        if item.src_path and item.src_path.samefile(img_path):
            item.cover_image_p = True
            find = True
            break
    if not find:
        if not img_path.is_relative_to(curdir):
            raise BuilderError(f'''All resouces should be in the descendant of the current directory.
  -- {str(img_path)}
  -- curdir: {curdir}''')
        
        manifest['pkg_items'].append(_ManifestItem(
            id = _next_id(manifest['pkg_items'][-1]),
            href = 'items/' + str(img_path.relative_to(curdir)),
            media_type = magic.from_file(str(img_path), mime=True),
            src_path = img_path,
            cover_image_p = True,
        ))

def _next_id(item: _ManifestItem) -> str:
    return f'item{str(int(item.id[4:])+1)}'



# Package directory utils

def _template(name: str) -> Template:
    filename = str(Path(__file__).parent / 'templates' / name)
    return Template(filename=filename)
    
def _make_build_dir(stem: Path, *candidates: str) -> Path: # failable
    assert len(candidates) > 0
    
    dest = stem / candidates[0]
    dotfile = dest / ('.' + app.__appname__)
    if not dest.exists():
        logger.info(f'making a build dir\n  -- {str(dest)}')
        dest.mkdir()
        dotfile.touch()
        return dest
    if dotfile.exists():
        return dest
    if len(candidates) > 1:
        return _make_build_dir(stem, *candidates[1:])

    logger.warning(f'A build dir should have a file "{dotfile.name}".')
    raise BuilderError(f'{app.__appname__} cannot make a build dir: {dest.resolve()}')

def _make_container_file(path: Path, pkg_doc: Path) -> None:
    pkg_doc_loc = str(pkg_doc.relative_to(path.parent.parent))
    template = _template(path.name)
    with open(path, 'w') as f:
        f.write(template.render(pkg_doc_loc=pkg_doc_loc))
        
    
