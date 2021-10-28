import unittest

import tinyepubbuilder.reader as r
import tinyepubbuilder.package as p

class TestFileListParser(unittest.TestCase):
    def setUp(self):
        self.parser = r.FileListParser()
        
    def test_initialize(self):
        self.assertTrue(isinstance(self.parser.parse(''), p.PackageSpec))

    def test_parse(self):
        with open('assets/spine.tsv') as f:
            self.parser.parse(f)
        

if __name__ == '__main__':
    unittest.main()
