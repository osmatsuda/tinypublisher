import unittest
import xml.etree.ElementTree as ET
import pathlib, logging

import tinypublisher as app
import tinypublisher.builder as b
import tinypublisher.reader as r


class TestBuilder2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r.logger.setLevel(logging.WARNING)
        b.logger.setLevel(logging.WARNING)
        
    def setUp(self):
        self.curdir = pathlib.Path(__file__).parent / 'assets2'
        self.parser = r.FileListParser(str(self.curdir))
        
        specfile = self.parser.curdir / 'spine.tsv'
        with open(specfile) as f:
            self.spec = self.parser.parse(f)

        self.builder = b.PackageBuilder('test')
        self.pkg_doc_path = self.curdir / 'build/test/book/package.opf'

    def make_pkg(self):
        self.spec.language_tag = None
        self.spec.uuid = app.__appname__ + '.test'
        self.spec.author = 'fu'
        self.spec.book_title = 'test of tinypublisher'

        self.builder.make_package_dirs(self.curdir)

    def test_package(self):
        with self.assertRaises(app.AppBaseError):
            self.make_pkg()
            self.builder.make_package_document(self.spec)
            self.builder.package_content_items(self.spec)

            items_dir = self.builder.destdir / 'book/items'
            self.assertEqual(len(list(items_dir.iterdir())),
                             len(list(self.curdir.iterdir())) - 2 + 3 + 1 - 1)

        
if __name__ == '__main__':
    unittest.main()
