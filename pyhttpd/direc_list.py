"""Render directory listings as HTML (in memory, never written to disk)."""
import os
import os.path
from datetime import datetime
from urllib.parse import quote

import jinja2

from . import imp_func


def get_path(path):
    if path.endswith('/'):
        path = path[:-1]
    return path


def get_time(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d  %H:%M")


def get_display_info(path):
    # Links are relative to the listing URL (which always ends in '/'), so the
    # server's filesystem layout never appears in the page.
    dis = dict(parent="../", p_name=os.path.basename(path), folder=[])
    with os.scandir(path) as it:
        for item in sorted(it, key=lambda e: e.name):
            fname = item.name
            if fname == imp_func.protect_file:
                continue  # never advertise the password file
            if item.is_dir():
                icon, alt, link = "icons/folder.gif", "[DIR]", quote(fname) + "/"
            else:
                icon, alt, link = "icons/file.gif", "[]", quote(fname)
            info = item.stat()
            dis["folder"].append(dict(name=fname, size=info.st_size,
                                      time=get_time(info.st_mtime), link=link,
                                      icon=icon, alt=alt))
    return dis


# autoescape: file names are untrusted and must not inject HTML into the page.
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(searchpath=os.path.join(imp_func.BASE_DIR, 'templates')),
    autoescape=True,
)
template = env.get_template('index_temp.html')


def dir_list(path):
    """Return the HTML listing for directory `path`."""
    return template.render(get_display_info(get_path(path)))
