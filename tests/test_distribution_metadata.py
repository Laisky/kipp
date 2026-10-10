"""Check the installed release metadata independently of source configuration."""

from importlib.metadata import metadata, version
import unittest

from packaging.requirements import Requirement

import kipp


class DistributionMetadataTests(unittest.TestCase):
    """DistributionMetadataTests preserves version, README and dependency contracts."""

    def test_installed_version_matches_public_package_version(self):
        """test_installed_version_matches_public_package_version rejects a stale installed release."""
        self.assertEqual(version("kipp"), kipp.__version__)

    def test_markdown_description_is_declared_for_publishers(self):
        """test_markdown_description_is_declared_for_publishers preserves correct rendering."""
        self.assertEqual(metadata("kipp")["Description-Content-Type"], "text/markdown")

    def test_supported_hash_versions_are_declared_without_allowing_major_four(self):
        """test_supported_hash_versions_are_declared_without_allowing_major_four guards actual wheel metadata."""
        requirements = [
            Requirement(line) for line in metadata("kipp").get_all("Requires-Dist", [])
        ]
        dependency = next(item for item in requirements if item.name == "xxhash")
        for supported in ("1.4.4", "2.0.2", "3.8.1"):
            with self.subTest(version=supported):
                self.assertIn(supported, dependency.specifier)
        self.assertNotIn("4.0.0", dependency.specifier)


if __name__ == "__main__":
    unittest.main()
