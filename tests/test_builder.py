import unittest
import pathlib
import xml.etree.ElementTree as ET
import zipfile

import tinyepubbuilder as app
import tinyepubbuilder.builder as b
import tinyepubbuilder.reader as r


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.curdir = pathlib.Path(__file__).parent / 'assets'
        self.parser = r.FileListParser(str(self.curdir))
        
        specfile = self.parser.curdir / 'spine.tsv'
        with open(specfile) as f:
            self.spec = self.parser.parse(f)

        self.builder = b.PackageBuilder('test')
        self.pkg_doc_path = self.curdir / 'build/test/book/package.opf'

    def make_pkg(self):
        self.spec.language_tag = None
        self.spec.uuid = app.__appname__ + '.test'
        self.builder.make_package_dirs(self.curdir)
        self.builder.make_package_document(self.spec)
        
    def test_init(self):
        self.builder.make_package_dirs(self.curdir)

        dest = self.curdir / 'build/test'
        container_xml = dest / 'META-INF/container.xml'
        self.assertTrue(container_xml.is_file())

        pkg_doc_loc = str((self.builder.destdir / 'book/package.opf').relative_to(dest))
        self.assertEqual(pkg_doc_loc, str(self.pkg_doc_path.relative_to(dest)))
        
        container_xml_tree = ET.parse(container_xml)
        container_xml_root = container_xml_tree.getroot()
        self.assertEqual(container_xml_root.find('.//{*}rootfile').get('full-path'), pkg_doc_loc)

    def test_package_document(self):
        self.make_pkg()

        self.assertTrue(self.pkg_doc_path.is_file())

        pkg_doc_tree = ET.parse(self.pkg_doc_path)
        self.assertEqual(len(pkg_doc_tree.findall('.//{*}manifest/{*}item')) - 1,
                         len(list(self.curdir.iterdir())) - 2 + 3)

        xhtmls = []
        for item in pkg_doc_tree.findall('.//{*}manifest/{*}item'):
            href = item.get('href')
            if not href.endswith('.xhtml'):
                continue
            xhtmls.append(href)
        self.assertEqual(xhtmls, ['navigation.xhtml', 'items/01.png.xhtml', 'items/02.xhtml',
                                  'items/04.svg.xhtml', 'items/05.jpg.xhtml'])

    def test_navigation(self):
        self.make_pkg()
        self.builder.make_navigation_document(self.spec)

        titles = ['The first page', 'tinyepubbuilder sample file: 02', '03.svg',
                  '04.svg', 'The last page']
        nav_doc = self.builder.destdir / 'book/navigation.xhtml'
        nav_tree = ET.parse(nav_doc)
        self.assertEqual([a.text for a in nav_tree.findall('.//{*}li/{*}a')],
                         titles)

    def test_package(self):
        self.make_pkg()
        self.builder.package_content_items(self.spec)

        items_dir = self.builder.destdir / 'book/items'
        self.assertEqual(len(list(items_dir.iterdir())),
                         len(list(self.curdir.iterdir())) - 2 + 3 + 1)
        # 3: wrapping xhtmls, 1: css for wrapping xhtml

    def test_zip(self):
        self.make_pkg()
        self.builder.package_content_items(self.spec)
        dest = self.builder.destdir.parent / (self.builder.destdir.name + '.epub')
        if dest.exists():
            dest.unlink()
        self.builder.zipup()

        with zipfile.ZipFile(dest) as zf:
            self.assertIsNone(zf.testzip())

if __name__ == '__main__':
    unittest.main()
