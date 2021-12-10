import unittest, logging
import pathlib, uuid

import tinyepubbuilder.reader as r
import tinyepubbuilder.package as p

class TestFileListParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r.logger.setLevel(logging.WARNING)
        
    def setUp(self):
        self.curdir = pathlib.Path(__file__).parent / 'assets'
        self.parser = r.FileListParser(str(self.curdir))
        
        specfile = self.parser.curdir / 'spine.tsv'
        with open(specfile) as f:
            self.spec = self.parser.parse(f)
        
    def test_initialize(self):
        self.assertTrue(isinstance(self.parser.parse(''), p.PackageSpec))

    def test_parse(self):
        spine = self.spec.spine
        self.assertEqual(spine[0].index_title, 'The first page')
        self.assertEqual(spine[1].index_title, 'tinyepubbuilder sample file: 02')
        self.assertEqual(spine[2].index_title, '03')
        self.assertEqual(spine[3].index_title, 'tinyepubbuilder sample image: 04')
        self.assertEqual(spine[3].content_caption, 'tinyepubbuilder sample image: 04')
        self.assertEqual(spine[4].content_caption, 'Goodbye<br/>Sayoonara')

        path_to_assets = self.parser.curdir.resolve()
        _02_includes = [str(path_to_assets / name)
                        for name in ['02.js', 'style.css', 'mark3.svg', 'star2.gif']]
        self.assertEqual(set([p for p, _ in spine[1].content_includes]),
                         set(_02_includes))
        self.assertTrue(spine[2].content_includes is None or
                        len(spine[2].content_includes) == 0)
        self.assertEqual(spine[3].content_includes[0][0],
                         str(path_to_assets / 'star1.gif'))

    def test_package(self):
        with self.assertRaises(p.PackageError):
            self.spec.cover_image = '01.jpg'

        self.spec.cover_image = '01.png'
        self.assertEqual(str(self.spec.cover_image.resolve()),
                         str(self.curdir.resolve() / '01.png'))

        self.spec.language_tag = None
        self.assertEqual(self.spec.language_tag, 'en')
        self.spec.id = None
        self.spec.uuid = 'osmatsuda.sakura.ne.jp'
        self.assertEqual(self.spec.id, uuid.uuid5(uuid.NAMESPACE_DNS, 'osmatsuda.sakura.ne.jp').urn)

if __name__ == '__main__':
    unittest.main()
