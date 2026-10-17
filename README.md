# file-metadata-extractor

A small Python library that returns file metadata (size, mtime, ctime, mode, uid, gid) as a dict from a single `os.stat` call.

## Usage

```python
from file_metadata_extractor import extract_metadata_dict, FileMetadataError

try:
    md = extract_metadata_dict("/path/to/file")
    print(md["size"], md["mtime"], md["uid"])
except FileMetadataError as exc:
    print("could not stat:", exc)
```

`extract_metadata` is a backwards-compatible alias for `extract_metadata_dict` and returns the same dict.

## Why

`os.stat` returns a `stat_result` tuple with fields positional and platform-dependent. This wrapper maps the commonly-used fields into a dict with stable names so callers can serialize or pick fields without remembering index order. It deliberately exposes a subset (size, mtime, ctime, mode, uid, gid) rather than every available field, to keep the output shape predictable across platforms.

The trade-off: you give up direct access to fields like inode or device number that some use cases need. If you need those, call `os.stat` directly.

## Edge cases

Symlinks are not followed by default. Pass `follow_symlinks=True` to resolve the link target. A dangling symlink with `follow_symlinks=True` raises `FileMetadataError`. Every `OSError` from the underlying stat call is wrapped in `FileMetadataError` with the original error preserved as `__cause__`.

Run tests with:

```
PYTHONPATH=src python -m unittest discover -s tests
```

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

