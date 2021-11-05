from tinyepubbuilder.package import PackageSpec

class PackageBuilder():
    def __init__(self, pkg_name: str) -> None:
        pass

    def make_package_dir(self) -> bool: # failable
        pass

    def build_with(self, spec: PackageSpec) -> None: # failable
        pass

    def zipup(self) -> None:
        pass

