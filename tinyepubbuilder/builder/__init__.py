from pathlib import Path
from mako.template import Template

import tinyepubbuilder as app
from tinyepubbuilder.package import PackageSpec

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

    def zipup(self) -> None:
        pass

    
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

    logger.info(f'a build dir should have a file "{dotfile.name}"')
    raise BuildingError(f'{app.__appname__} cannot make a build dir: {dest.resolve()}')

def _make_container_file(path: Path, pkg_doc: Path) -> None:
    pkg_doc_loc = str(pkg_doc.relative_to(path.parent.parent))
    template = Template(filename=str(Path(__file__).parent / 'templates' / path.name))
    with open(path, 'w') as f:
        f.write(template.render(pkg_doc_loc=pkg_doc_loc))
    
