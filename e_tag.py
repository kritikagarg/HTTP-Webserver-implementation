import hashlib

import fs


def gen_etag(content):
    """Strong ETag: content hash plus inode and mtime (changes if the file moves or is modified)."""
    md = hashlib.md5(fs.read(content)).hexdigest()
    st = f"{fs.inode(content):x}{int(fs.mtime(content)):x}"
    return f'"{md}-{st}"'
