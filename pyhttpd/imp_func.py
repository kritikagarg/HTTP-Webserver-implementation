"""Shared configuration, path resolution and logging helpers."""
import datetime
import os
import os.path
import threading
from urllib.parse import urlparse, unquote

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # the pyhttpd package
PROJECT_DIR = os.path.dirname(BASE_DIR)                          # repository root
CONFIG_DIR = os.getenv("CONFIG_DIR", os.path.join(BASE_DIR, "config"))

# Virtual URI that serves the access log.
virtual_uri = "/.well-known/access.log"

# Name used for generated directory listings. It contains a NUL byte, so it can
# never collide with a real file and is never written to disk.
LISTING_NAME = "\x00listing.html"


class Forbidden(Exception):
    """The request path resolves outside the document root."""


def load_yaml(config='check.yaml'):
    with open(os.path.join(CONFIG_DIR, config), 'r') as f:
        return yaml.safe_load(f)


main_dict = load_yaml()

# Paths and secrets come from the environment; check.yaml only holds protocol data.
docroot = os.path.realpath(os.getenv("DOCROOT", os.path.join(PROJECT_DIR, "www")))
log_dir = os.getenv("LOG_DIR", os.path.join(PROJECT_DIR, "logs"))
log_path = os.path.join(log_dir, main_dict['log_file'])
protect_file = os.getenv("PROTECT_FILE", main_dict['protect_file'])


def check_log_path(c_path, method):
    return c_path == virtual_uri and method == 'GET'


def ext_path(uri):
    # Paths are percent-decoded with unquote, not unquote_plus: '+' is a literal
    # character in a URL path (RFC 3986), not an encoded space.
    return unquote(urlparse(uri).path)


def resolve(c_path):
    """Map a decoded URL path to a filesystem path inside the document root.

    Resolves '..' segments and symlinks, then refuses anything that lands
    outside the document root. Keeps a trailing '/' so directory handling
    still knows whether the client asked for 'dir' or 'dir/'.
    """
    if "\x00" in c_path:
        raise Forbidden(c_path)
    full = os.path.realpath(os.path.join(docroot, c_path.lstrip("/")))
    if full != docroot and not full.startswith(docroot + os.sep):
        raise Forbidden(c_path)
    if c_path.endswith("/") and not full.endswith("/"):
        full += "/"
    return full


def get_content(req):
    uri = req[0][1]
    method = req[0][0]
    c_path = ext_path(uri)
    if check_log_path(c_path, method):
        return log_path, c_path
    content = resolve(c_path)
    if os.path.isdir(content) and content.endswith('/'):
        if os.path.exists(content + "index.html"):
            content = content + "index.html"
        else:
            content = content + LISTING_NAME
    return content, c_path


def connect(req):
    connection = "keep-alive"
    for tup in req:
        if tup[0] == "connection":
            connection = tup[1]
    return connection


def get_reqheader_value(header, req):
    """All (name, value) pairs for one header name (exact match)."""
    return [tup for tup in req[1:] if tup[0] == header]


_log_lock = threading.Lock()


def log_dump(ip, req, sc, ld, uid="-", uname="-", logfile=None):
    """Write one Common Log Format line. A lock keeps lines from interleaving."""
    rl = " ".join(req[0]) if isinstance(req[0], tuple) else str(req[0])
    logdate = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
    line = f'{ip} {uid} {uname} [{logdate}] "{rl}" {sc} {ld.get("content_length", "-")}\n'
    if logfile is None:
        return
    with _log_lock:
        logfile.write(line)
        logfile.flush()
