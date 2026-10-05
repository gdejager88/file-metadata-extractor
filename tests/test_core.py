import os
import stat as stat_module
import tempfile
import unittest

from file_metadata_extractor import (
    extract_metadata,
    extract_metadata_dict,
    FileMetadataError,
)


class TestExtractMetadata(unittest.TestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        self.base = self._tempdir.name

    def _make_file(self, name, content=b"hello"):
        path = os.path.join(self.base, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def _make_dir(self, name):
        path = os.path.join(self.base, name)
        os.mkdir(path)
        return path

    def _make_symlink(self, name, target):
        path = os.path.join(self.base, name)
        os.symlink(target, path)
        return path

    def test_returns_all_expected_keys(self):
        p = self._make_file("a.txt")
        d = extract_metadata_dict(p)
        self.assertEqual(
            set(d.keys()),
            {"size", "mtime", "ctime", "mode", "uid", "gid"},
        )

    def test_size_matches_file_content(self):
        p = self._make_file("b.txt", content=b"\x00" * 4096)
        d = extract_metadata_dict(p)
        self.assertEqual(d["size"], 4096)

    def test_mode_matches_stat_module(self):
        p = self._make_file("c.txt")
        d = extract_metadata_dict(p)
        raw_mode = os.lstat(p).st_mode
        self.assertEqual(d["mode"], raw_mode)
        self.assertTrue(stat_module.S_ISREG(d["mode"]))

    def test_directory_mode_detected(self):
        p = self._make_dir("a_dir")
        d = extract_metadata_dict(p)
        self.assertTrue(stat_module.S_ISDIR(d["mode"]))

    def test_mtime_and_ctime_are_floats(self):
        p = self._make_file("d.txt")
        d = extract_metadata_dict(p)
        self.assertIsInstance(d["mtime"], float)
        self.assertIsInstance(d["ctime"], float)

    def test_mtime_reasonable_recent(self):
        """mtime should be close to the time the file was created.

        We bound it rather than asserting equality, because filesystem
        resolution varies and the act of stat-ing can update ctime.
        """
        import time
        before = time.time()
        p = self._make_file("e.txt")
        d = extract_metadata_dict(p)
        after = time.time()
        self.assertLessEqual(d["mtime"], after + 2)
        self.assertGreaterEqual(d["mtime"], before - 2)

    def test_uid_gid_match_stat(self):
        p = self._make_file("f.txt")
        d = extract_metadata_dict(p)
        raw = os.lstat(p)
        self.assertEqual(d["uid"], raw.st_uid)
        self.assertEqual(d["gid"], raw.st_gid)

    def test_missing_path_raises_file_metadata_error(self):
        with self.assertRaises(FileMetadataError):
            extract_metadata_dict(os.path.join(self.base, "nope.txt"))

    def test_symlink_default_does_not_follow(self):
        target = self._make_file("target.txt", content=b"data")
        link = self._make_symlink("link", target)
        d = extract_metadata_dict(link)
        # lstat on a symlink returns mode with S_IFLNK set
        self.assertTrue(stat_module.S_ISLNK(d["mode"]))
        self.assertNotEqual(d["size"], len(b"data"))

    def test_symlink_followed_when_requested(self):
        target = self._make_file("target2.txt", content=b"data")
        link = self._make_symlink("link2", target)
        d = extract_metadata_dict(link, follow_symlinks=True)
        self.assertEqual(d["size"], len(b"data"))
        self.assertFalse(stat_module.S_ISLNK(d["mode"]))

    def test_symlink_to_missing_with_follow_raises(self):
        link = self._make_symlink(
            "dangling",
            os.path.join(self.base, "nonexistent_target"),
        )
        with self.assertRaises(FileMetadataError):
            extract_metadata_dict(link, follow_symlinks=True)

    def test_alias_returns_same_dict(self):
        p = self._make_file("g.txt")
        via_dict = extract_metadata_dict(p)
        via_alias = extract_metadata(p)
        self.assertEqual(via_dict, via_alias)

    def test_chained_cause_preserved(self):
        try:
            extract_metadata_dict(os.path.join(self.base, "missing.bin"))
        except FileMetadataError as exc:
            self.assertIsNotNone(exc.__cause__)
            self.assertIsInstance(exc.__cause__, OSError)
        else:
            self.fail("expected FileMetadataError")


if __name__ == "__main__":
    unittest.main()
