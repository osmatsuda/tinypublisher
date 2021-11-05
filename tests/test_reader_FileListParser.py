import unittest

import tinyepubbuilder.reader as r
import tinyepubbuilder.package as p

class TestFileListParser(unittest.TestCase):
    def setUp(self):
        self.parser = r.FileListParser()
        
    def test_initialize(self):
        self.assertTrue(isinstance(self.parser.parse(''), p.PackageSpeck))

    def test_parse(self):
        with open('assets/spine.tsv') as f:
            spine = self.parser.parse(f).spine
        self.assertTrue(spine[1].title is None)
        self.assertEqual(spine[2].title, 'Content Document SVG')
        self.assertEqual(spine[4].caption, 'Goodbye<br/>Sayoonara')

if __name__ == '__main__':
    unittest.main()
