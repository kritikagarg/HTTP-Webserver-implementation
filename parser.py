"""HTTP/1.1 message framing and request parsing (RFC 9112).

Reader pulls complete messages off a socket: the header block up to the blank
line, then exactly the body the headers announce (Content-Length or chunked).
Leftover bytes stay buffered for the next pipelined request.
"""
import os
import re

MAX_HEADER_BYTES = int(os.getenv("MAX_HEADER_BYTES", 16 * 1024))
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", 10 * 1024 * 1024))

HEADER_END = re.compile(rb"\r?\n\r?\n")
TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
REQUEST_LINE = re.compile(r"^([A-Z]+)\s+(\S+)\s+([\w\/\.]+)$")


class HTTPError(Exception):
    """A framing error; the server answers with `status` and closes the connection."""

    def __init__(self, status):
        super().__init__(status)
        self.status = status


class ConnectionClosed(Exception):
    pass


class Reader:
    def __init__(self, sock):
        self.sock = sock
        self.buf = b""

    def _fill(self):
        data = self.sock.recv(65536)
        if not data:
            raise ConnectionClosed()
        self.buf += data

    def has_buffered(self):
        return bool(self.buf)

    def read_head(self):
        """Return the raw header block (without the terminating blank line)."""
        while True:
            # RFC 9112 2.2: ignore empty lines before the request line.
            self.buf = self.buf.lstrip(b"\r\n")
            m = HEADER_END.search(self.buf)
            if m:
                if m.start() > MAX_HEADER_BYTES:
                    raise HTTPError(431)
                head, self.buf = self.buf[:m.start()], self.buf[m.end():]
                return head
            if len(self.buf) > MAX_HEADER_BYTES:
                raise HTTPError(431)
            self._fill()

    def read_exact(self, n):
        while len(self.buf) < n:
            self._fill()
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def read_line(self, limit=4096):
        while b"\n" not in self.buf:
            if len(self.buf) > limit:
                raise HTTPError(400)
            self._fill()
        line, _, self.buf = self.buf.partition(b"\n")
        return line.rstrip(b"\r")

    def read_chunked(self):
        body = b""
        while True:
            size_field = self.read_line().split(b";", 1)[0].strip()  # ignore chunk extensions
            if not re.fullmatch(rb"[0-9A-Fa-f]{1,16}", size_field):
                raise HTTPError(400)
            size = int(size_field, 16)
            if size == 0:
                while self.read_line() != b"":  # discard trailer fields
                    pass
                return body
            if len(body) + size > MAX_BODY_BYTES:
                raise HTTPError(413)
            body += self.read_exact(size)
            if self.read_line() != b"":
                raise HTTPError(400)


def request_parser(head):
    """Parse a header block into the server's request form.

    req[0] is (method, target, version) and the rest are (lowercase-name, value)
    pairs. bad_req is set for messages that must get a 400.
    """
    text = head.decode("utf-8", "surrogateescape")
    lines = text.split("\n")
    bad = False
    req_line = lines[0].rstrip("\r")
    m = REQUEST_LINE.match(req_line)
    req = [(m[1], m[2], m[3])] if m else [req_line]
    if not m:
        bad = True
    for line in lines[1:]:
        line = line.rstrip("\r")
        if line[:1] in (" ", "\t"):
            bad = True  # obsolete line folding is rejected (RFC 9112 5.2)
            continue
        name, colon, value = line.partition(":")
        # No whitespace is allowed between the field name and the colon (RFC 9112 5.1).
        if not colon or not TOKEN.match(name):
            bad = True
            continue
        req.append((name.lower(), value.strip(" \t")))
    return dict(req=req, bad_req=bad)


def body_length(req):
    """Decide how the body is framed: ('chunked', None), ('length', n) or (None, 0).

    Raises HTTPError for messages that are ambiguous or unsupported. A request
    with both Transfer-Encoding and Content-Length is refused, because servers
    and proxies that disagree on which one wins can be exploited with request
    smuggling (RFC 9112 6.1).
    """
    te = [v for n, v in req[1:] if n == "transfer-encoding"]
    cl = [v for n, v in req[1:] if n == "content-length"]
    if te and cl:
        raise HTTPError(400)
    if te:
        codings = [c.strip().lower() for v in te for c in v.split(",") if c.strip()]
        if codings != ["chunked"]:
            raise HTTPError(501 if codings and codings[-1] == "chunked" else 400)
        return "chunked", None
    if cl:
        values = {c.strip() for v in cl for c in v.split(",")}
        if len(values) != 1 or not next(iter(values)).isdigit():
            raise HTTPError(400)
        n = int(values.pop())
        if n > MAX_BODY_BYTES:
            raise HTTPError(413)
        return "length", n
    return None, 0
