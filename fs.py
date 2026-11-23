"""File access that also understands virtual directory listings.

A directory listing is rendered in memory when it is needed instead of being
written into the served directory as a temporary file.
"""
import os

import imp_func
import direc_list


def is_listing(path):
    return path.endswith(imp_func.LISTING_NAME)


def _real(path):
    return path[:-len(imp_func.LISTING_NAME)] if is_listing(path) else path


def exists(path):
    if is_listing(path):
        return os.path.isdir(_real(path))
    return os.path.exists(path)


def mtime(path):
    return os.stat(_real(path)).st_mtime


def inode(path):
    return os.stat(_real(path)).st_ino


def read(path):
    if is_listing(path):
        return direc_list.dir_list(_real(path)).encode("utf-8")
    with open(path, "rb") as f:
        return f.read()


def size(path):
    if is_listing(path):
        return len(read(path))
    return os.path.getsize(path)
