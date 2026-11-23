"""Byte-range requests (single range).

The parsed range is returned to the caller rather than stored in a module-level
dict, so concurrent requests can't overwrite each other's range.
"""
import re

import fs


def parse_range(req):
    """Return (start, end) from a 'Range: bytes=...' header, or None.

    end is None for open-ended ranges ("100-"); start is negative for suffix
    ranges ("-100"). Multiple or malformed ranges return None, and the server
    then ignores the header and sends the full representation (allowed by RFC 9110 14.2).
    """
    for name, value in req[1:]:
        if name != "range":
            continue
        unit, _, spec = value.partition("=")
        if unit.strip().lower() != "bytes" or "," in spec:
            return None
        spec = spec.strip()
        m = re.fullmatch(r"(\d+)-(\d*)", spec)
        if m:
            start = int(m[1])
            end = int(m[2]) if m[2] else None
            if end is not None and end < start:
                return None
            return start, end
        m = re.fullmatch(r"-(\d+)", spec)
        if m and int(m[1]) > 0:
            return -int(m[1]), None
        return None
    return None


def check_partial(req):
    return 206 if parse_range(req) else 200


def partial_content(method, content, req):
    """Return (payload, content_length, content_range, satisfiable)."""
    size = fs.size(content)
    start, end = parse_range(req)
    if start < 0:
        start = max(size + start, 0)
        end = size - 1
    elif end is None or end >= size:
        end = size - 1
    if size == 0 or start >= size:
        return b"", 0, f"bytes */{size}", False
    data = fs.read(content)[start:end + 1]
    return data, len(data), f"bytes {start}-{end}/{size}", True
