"""Core metadata extraction for filesystem paths.

A thin wrapper over os.stat that returns a dict instead of a stat_result,
so callers can serialise or pick fields by name without remembering the
position of each tuple element.
"""

import os
import stat as stat_module


class FileMetadataError(Exception):
    """Base error for this package. Wrap everything we raise so callers
    can catch a single type.
    """
    pass


# Field order is fixed so callers and tests can rely on key existence.
# We expose the subset of stat fields that are meaningful on every POSIX
# platform the standard library targets; we deliberately do NOT include
# fields like atime or inode that vary in usefulness across filesystems.
_FIELDS = ("size", "mtime", "ctime", "mode", "uid", "gid")


def _stat_to_metadata(st):
    """Convert a single stat_result into the metadata dict shape.

    Returns a tuple in the same order as _FIELDS so the public caller
    gets a dict with stable key insertion order across Python versions.
    """
    return (
        st.st_size,
        st.st_mtime,
        st.st_ctime,
        st.st_mode,
        st.st_uid,
        st.st_gid,
    )


def extract_metadata_dict(path, follow_symlinks=False):
    """Return a dict of file metadata for *path*.

    Performs exactly one os.stat call (or os.lstat when follow_symlinks is
    False). Keys: size, mtime, ctime, mode, uid, gid. Times are POSIX
    timestamps (float seconds).

    follow_symlinks=False is the default because silently following links
    is a common source of surprising metadata; callers who want link
    resolution opt in explicitly.

    Raises FileMetadataError on any OSError from the underlying call, with
    the original error chained as __cause__.
    """
    try:
        if follow_symlinks:
            st = os.stat(path)
        else:
            st = os.lstat(path)
    except OSError as exc:
        raise FileMetadataError(str(exc)) from exc

    values = _stat_to_metadata(st)
    return dict(zip(_FIELDS, values))


def extract_metadata(path, follow_symlinks=False):
    """Backward-compatible alias for extract_metadata_dict.

    The package historically exposed this name. Kept so existing callers
    don't break; new code should prefer extract_metadata_dict for clarity.
    """
    return extract_metadata_dict(path, follow_symlinks=follow_symlinks)
