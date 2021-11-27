import unittest

import tinyepubbuilder.reader as r
import tinyepubbuilder.package as p
import pathlib

class TestFileListParser(unittest.TestCase):
    def setUp(self):
        curdir = pathlib.Path(__file__).parent / 'assets'
        self.parser = r.FileListParser(str(curdir))
        
    def test_initialize(self):
        self.assertTrue(isinstance(self.parser.parse(''), p.PackageSpec))

    def test_parse(self):
        specfile = self.parser.curdir / 'spine.tsv'
        with open(specfile) as f:
            spine = self.parser.parse(f).spine
        self.assertEqual(spine[0].index_title, 'The first page')
        self.assertEqual(spine[1].index_title, 'tinyepubbuilder sample file: 02')
        self.assertEqual(spine[2].index_title, '03')
        self.assertEqual(spine[3].index_title, 'tinyepubbuilder sample image: 04')
        self.assertEqual(spine[3].content_caption, 'tinyepubbuilder sample image: 04')
        self.assertEqual(spine[4].content_caption, 'Goodbye<br/>Sayoonara')

        _02_includes = [str(self.parser.curdir.absolute() / name)
                        for name in ['style.css', 'mark3.svg', 'star2.gif']]
        self.assertEqual(set(spine[1].content_includes), set(_02_includes))

if __name__ == '__main__':
    unittest.main()
