"""PUT and DELETE. Authorization is checked by authorize.py before these run."""
import os
import tempfile

import fs


def put(content, client_payload):
    if content.endswith('/') or fs.is_listing(content) or os.path.isdir(content):
        return 405
    parent = os.path.dirname(content)
    if not os.path.isdir(parent):
        return 409  # Conflict: the parent collection doesn't exist
    existed = os.path.isfile(content)
    # Write to a temp file and rename, so a concurrent GET never sees a half-written file.
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".put-")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(client_payload or b"")
        os.replace(tmp, content)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return 200 if existed else 201


def delete(content):
    if os.path.isfile(content):
        os.remove(content)
        return 200
    return 404


def unsafe_method_handler(req, client_payload, content):
    method = req[0][0]
    if method == "DELETE":
        return delete(content)
    if method == "PUT":
        return put(content, client_payload)
    return 405
