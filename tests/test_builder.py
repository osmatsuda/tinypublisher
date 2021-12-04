import unittest
import pathlib
import xml.etree.ElementTree as ET

import tinyepubbuilder.builder as b
import tinyepubbuilder.reader as r


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.curdir = pathlib.Path(__file__).parent / 'assets'
        self.parser = r.FileListParser(str(self.curdir))
        
        specfile = self.parser.curdir / 'spine.tsv'
        with open(specfile) as f:
            self.spec = self.parser.parse(f)
        
    def test_init(self):
        builder = b.PackageBuilder('test')
        builder.make_package_dirs(self.curdir)

        dest = self.curdir / 'build/test'
        container_xml = dest / 'META-INF/container.xml'
        self.assertTrue(container_xml.is_file())

        pkg_doc_loc = str(builder.package_doc.relative_to(dest))
        self.assertEqual(pkg_doc_loc, 'book/package.opf')
        
        container_xml_tree = ET.parse(container_xml)
        container_xml_root = container_xml_tree.getroot()
        self.assertEqual(container_xml_root.find('.//{*}rootfile').get('full-path'), pkg_doc_loc)
        

if __name__ == '__main__':
    unittest.main()
