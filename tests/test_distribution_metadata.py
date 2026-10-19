"""Check the installed release metadata independently of source configuration."""

from importlib.metadata import metadata, version
import unittest

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

import kipp


class DistributionMetadataTests(unittest.TestCase):
    """DistributionMetadataTests preserves version, README and dependency contracts."""

    def test_installed_version_matches_public_package_version(self):
        """test_installed_version_matches_public_package_version rejects a stale installed release."""
        self.assertEqual(version("kipp"), kipp.__version__)

    def test_markdown_description_is_declared_for_publishers(self):
        """test_markdown_description_is_declared_for_publishers preserves correct rendering."""
        self.assertEqual(metadata("kipp")["Description-Content-Type"], "text/markdown")

    def test_supported_hash_versions_are_declared_without_allowing_major_five(self):
        """test_supported_hash_versions_are_declared_without_allowing_major_five guards actual wheel metadata."""
        requirements = [
            Requirement(line) for line in metadata("kipp").get_all("Requires-Dist", [])
        ]
        dependency = next(item for item in requirements if item.name == "xxhash")
        for supported in ("1.4.4", "2.0.2", "3.8.1", "4.0.1"):
            with self.subTest(version=supported):
                self.assertIn(supported, dependency.specifier)
        self.assertNotIn("5.0.0", dependency.specifier)

    def test_python_floor_matches_the_modern_public_api(self):
        requirement = SpecifierSet(metadata("kipp")["Requires-Python"])
        self.assertIn("3.10", requirement)
        self.assertIn("3.15", requirement)
        self.assertNotIn("3.9", requirement)

    def test_optional_features_have_consistent_current_dependencies(self):
        requirements = [
            Requirement(line) for line in metadata("kipp").get_all("Requires-Dist", [])
        ]
        base = [r for r in requirements if r.marker is None]
        aio = [
            r
            for r in requirements
            if r.marker is not None and r.marker.evaluate({"extra": "aio"})
        ]
        for requirement in base + aio:
            if requirement.name == "tornado":
                self.assertIn("6.5.10", requirement.specifier)
                self.assertNotIn("4.5.3", requirement.specifier)
        image = next(
            r
            for r in requirements
            if r.name.lower() == "pillow" and r.marker.evaluate({"extra": "image"})
        )
        self.assertIn("12.3.0", image.specifier)
        self.assertNotIn("3.4.2", image.specifier)
        self.assertFalse({"future", "ruamel.yaml", "zipp"} & {r.name for r in base})


if __name__ == "__main__":
    unittest.main()
