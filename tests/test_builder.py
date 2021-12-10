import unittest
import pathlib
import xml.etree.ElementTree as ET

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
            
        self.pkg_doc_path = self.curdir / 'build/test/book/package.opf'
        
    def test_init(self):
        builder = b.PackageBuilder('test')
        builder.make_package_dirs(self.curdir)

        dest = self.curdir / 'build/test'
        container_xml = dest / 'META-INF/container.xml'
        self.assertTrue(container_xml.is_file())

        pkg_doc_loc = str(builder.package_doc.relative_to(dest))
        self.assertEqual(pkg_doc_loc, str(self.pkg_doc_path.relative_to(dest)))
        
        container_xml_tree = ET.parse(container_xml)
        container_xml_root = container_xml_tree.getroot()
        self.assertEqual(container_xml_root.find('.//{*}rootfile').get('full-path'), pkg_doc_loc)

    def test_package_document(self):
        self.spec.language_tag = None
        self.spec.uuid = app.__appname__ + '.test'

        builder = b.PackageBuilder('test')
        builder.make_package_dirs(self.curdir)
        builder.make_package_document(self.spec)

        self.assertTrue(self.pkg_doc_path.is_file())

        pkg_doc_tree = ET.parse(self.pkg_doc_path)
        self.assertEqual(len(pkg_doc_tree.findall('.//{*}manifest/{*}item')) - 1,
                         len(list(self.curdir.iterdir())) - 2)

if __name__ == '__main__':
    unittest.main()
