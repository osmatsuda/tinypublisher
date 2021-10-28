from dataclasses import dataclass
import io, csv

from tinyepubbuilder.package import PackageSpec

@dataclass
class _Status:
    line: int
    column: int

class FileListParser:
    def __init__(self):
        self.status = None

    def parse(self, fileobj: io.TextIOBase) -> PackageSpec:
        lines = csv.reader(fileobj, delimiter="\t")
        spec = PackageSpec()
        for entry in lines:
            if entry:
                self.parseEntry(entry, spec)
        return spec
    
    def parseText(self, text: str) -> PackageSpec:
        return self.parse(io.StringIO(text))

    def parseEntry(self, entry: list[str], spec: PackageSpec) -> None:
        pass
