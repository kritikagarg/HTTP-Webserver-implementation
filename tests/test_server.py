"""End-to-end tests: start the real server and talk to it over raw sockets.

Run with:  python -m pytest tests/
"""
import base64
import hashlib
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
from email.utils import parsedate_to_datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASIC = "Basic " + base64.b64encode(b"demo:demo").decode()


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    base = tmp_path_factory.mktemp("srv")
    docroot = base / "www"
    shutil.copytree(os.path.join(ROOT, "www"), docroot)
    (base / "outside.txt").write_text("outside the docroot\n")
    os.symlink(base / "outside.txt", docroot / "link-out.txt")
    # Digest-protected area
    digest_dir = docroot / "digest"
    digest_dir.mkdir()
    (digest_dir / "page.html").write_text("<p>digest ok</p>\n")
    (digest_dir / ".protected").write_text(
        'authorization-type=Digest\nrealm="Test Realm"\n'
        f'alice:Test Realm:{md5("alice:Test Realm:wonderland")}\n')
    # A file name full of HTML, for the listing-escaping test
    (docroot / "files" / "<em>bold&amp.txt").write_text("x\n")
    # CGI script whose name contains shell metacharacters
    evil = docroot / "cgi" / "x;touch PWNED.cgi"
    evil.write_text("#!/bin/sh\nprintf 'Content-Type: text/plain\\n\\nran\\n'\n")
    evil.chmod(evil.stat().st_mode | stat.S_IEXEC)

    port = free_port()
    env = dict(os.environ, DOCROOT=str(docroot), LOG_DIR=str(base / "logs"),
               NONCE_SECRET="test-secret", MAX_BODY_BYTES="65536")
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py"), "127.0.0.1", str(port)],
                            cwd=str(base), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("server did not start: " + proc.stdout.read().decode())
    yield dict(port=port, docroot=docroot, base=base)
    proc.kill()


def exchange(server, raw, timeout=3, pieces=None, delay=0.0):
    """Send raw bytes (optionally in pieces with a delay) and read until the server closes."""
    s = socket.create_connection(("127.0.0.1", server["port"]))
    s.settimeout(timeout)
    for i, part in enumerate(pieces or [raw]):
        if i:
            time.sleep(delay)
        s.sendall(part)
    out = b""
    try:
        while True:
            d = s.recv(65536)
            if not d:
                break
            out += d
    except socket.timeout:
        pass
    s.close()
    return out


def request(server, method, path, headers=None, body=b"", close=True):
    h = {"Host": "localhost"}
    if close:
        h["Connection"] = "close"
    h.update(headers or {})
    if body and "Content-Length" not in h and "Transfer-Encoding" not in h:
        h["Content-Length"] = str(len(body))
    head = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in h.items()) + "\r\n"
    return parse(exchange(server, head.encode() + body))


def parse(raw):
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split()[1]) if lines[0] else None
    headers = {}
    for line in lines[1:]:
        k, _, v = line.partition(":")
        headers[k.strip().lower()] = v.strip()
    return status, headers, body


def dechunk(body):
    out = b""
    while True:
        size_line, _, body = body.partition(b"\r\n")
        size = int(size_line, 16)
        if size == 0:
            return out
        out += body[:size]
        body = body[size + 2:]


# ---------------------------------------------------------------- basics

def test_get_index(server):
    status, headers, body = request(server, "GET", "/")
    assert status == 200 and b"It works" in body


def test_date_header_is_current(server):
    _, headers, _ = request(server, "GET", "/")
    sent = parsedate_to_datetime(headers["date"]).timestamp()
    assert abs(sent - time.time()) < 60


def test_head_has_no_body(server):
    status, headers, body = request(server, "HEAD", "/index.html")
    assert status == 200 and body == b"" and int(headers["content-length"]) > 0


def test_unknown_headers_are_ignored(server):
    status, _, _ = request(server, "GET", "/", {"Sec-Fetch-Mode": "navigate", "X-Anything": "1"})
    assert status == 200


def test_version_method_and_host_checks(server):
    assert parse(exchange(server, b"GET / HTTP/1.0\r\nHost: x\r\nConnection: close\r\n\r\n"))[0] == 505
    assert request(server, "BREW", "/")[0] == 501
    assert parse(exchange(server, b"GET / HTTP/1.1\r\nConnection: close\r\n\r\n"))[0] == 400


def test_redirect_rule(server):
    status, headers, _ = request(server, "GET", "/old-page.html")
    assert status == 301 and headers["location"] == "/index.html"


def test_content_negotiation(server):
    status, headers, body = request(server, "GET", "/greeting.html", {"Accept-Language": "es; q=1.0, en; q=0.5"})
    assert status == 200 and b"Hola" in body


# ---------------------------------------------------------------- path containment

@pytest.mark.parametrize("path", [
    "/../outside.txt",
    "/%2e%2e/outside.txt",
    "/files/../../outside.txt",
    "/%2e%2e%2f%2e%2e%2fetc/passwd",
    "/link-out.txt",            # symlink pointing outside the docroot
    "/files/%00listing.html",   # NUL byte
])
def test_path_traversal_is_blocked(server, path):
    status, _, body = request(server, "GET", path)
    assert status == 403
    assert b"outside the docroot" not in body
    assert request(server, "GET", "/")[0] == 200  # server still healthy


def test_protection_file_is_never_served(server):
    status, _, body = request(server, "GET", "/private/.protected", {"Authorization": BASIC})
    assert status == 403 and b"demo:" not in body


# ---------------------------------------------------------------- PUT / DELETE authorization

def test_put_and_delete_refused_outside_protected_dirs(server):
    assert request(server, "PUT", "/files/new.txt", body=b"hi")[0] == 405
    assert not (server["docroot"] / "files" / "new.txt").exists()
    assert request(server, "DELETE", "/files/sample.txt")[0] == 405
    assert (server["docroot"] / "files" / "sample.txt").exists()


def test_put_requires_auth_and_writes_nothing_without_it(server):
    status, headers, _ = request(server, "PUT", "/private/upload.txt", body=b"nope")
    assert status == 401 and "basic" in headers["www-authenticate"].lower()
    assert not (server["docroot"] / "private" / "upload.txt").exists()


def test_authorized_put_and_delete(server):
    target = server["docroot"] / "private" / "upload.txt"
    assert request(server, "PUT", "/private/upload.txt", {"Authorization": BASIC}, b"v1")[0] == 201
    assert request(server, "PUT", "/private/upload.txt", {"Authorization": BASIC}, b"v2")[0] == 200
    assert target.read_bytes() == b"v2"
    assert request(server, "DELETE", "/private/upload.txt")[0] == 401
    assert target.exists()
    assert request(server, "DELETE", "/private/upload.txt", {"Authorization": BASIC})[0] == 200
    assert not target.exists()


def test_basic_auth_rejects_wrong_or_prefix_usernames(server):
    for creds in (b"demo:wrong", b"dem:demo", b"garbage"):
        auth = "Basic " + base64.b64encode(creds).decode()
        assert request(server, "GET", "/private/secret.html", {"Authorization": auth})[0] == 401
    assert request(server, "GET", "/private/secret.html", {"Authorization": "Basic !!!"})[0] == 401
    assert request(server, "GET", "/private/secret.html", {"Authorization": BASIC})[0] == 200


def test_digest_auth_and_replay_protection(server):
    uri = "/digest/page.html"
    _, headers, _ = request(server, "GET", uri)
    nonce = re.search(r'nonce="([^"]+)"', headers["www-authenticate"])[1]

    def auth(nc, for_uri=uri):
        ha1 = md5("alice:Test Realm:wonderland")
        resp = md5(f"{ha1}:{nonce}:{nc}:xyz:auth:{md5('GET:' + for_uri)}")
        return {"Authorization": f'Digest username="alice", realm="Test Realm", nonce="{nonce}", '
                                 f'uri="{for_uri}", qop=auth, nc={nc}, cnonce="xyz", response="{resp}"'}

    status, headers, body = request(server, "GET", uri, auth("00000001"))
    assert status == 200 and b"digest ok" in body and "rspauth" in headers["authentication-info"]
    assert request(server, "GET", uri, auth("00000001"))[0] == 401   # replayed nonce-count
    assert request(server, "GET", uri, auth("00000002"))[0] == 200
    # A valid digest for one URI must not unlock another.
    assert request(server, "GET", "/digest/other.html", auth("00000003"))[0] == 401


# ---------------------------------------------------------------- request framing

def test_slow_client_split_across_packets(server):
    raw = b"GET /index.html HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"
    pieces = [raw[:10], raw[10:30], raw[30:]]
    status, _, body = parse(exchange(server, raw, pieces=pieces, delay=0.2))
    assert status == 200 and b"It works" in body


def test_body_arriving_after_headers(server):
    head = (b"PUT /private/slow.txt HTTP/1.1\r\nHost: x\r\nConnection: close\r\n"
            b"Authorization: " + BASIC.encode() + b"\r\nContent-Length: 10\r\n\r\n")
    status, _, _ = parse(exchange(server, None, pieces=[head, b"01234", b"56789"], delay=0.2))
    assert status == 201
    assert (server["docroot"] / "private" / "slow.txt").read_bytes() == b"0123456789"


def test_pipelined_requests(server):
    raw = (b"GET /index.html HTTP/1.1\r\nHost: x\r\n\r\n"
           b"HEAD /files/sample.txt HTTP/1.1\r\nHost: x\r\n\r\n"
           b"GET /old-page.html HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    out = exchange(server, raw)
    assert [int(m) for m in re.findall(rb"HTTP/1\.1 (\d{3})", out)] == [200, 200, 301]


def test_chunked_request_body(server):
    body = b"5\r\nhello\r\n6;ext=1\r\n world\r\n0\r\n\r\n"
    status, _, _ = request(server, "PUT", "/private/chunked.txt",
                           {"Authorization": BASIC, "Transfer-Encoding": "chunked"}, body)
    assert status == 201
    assert (server["docroot"] / "private" / "chunked.txt").read_bytes() == b"hello world"


def test_content_length_with_transfer_encoding_is_rejected(server):
    raw = (b"POST /index.html HTTP/1.1\r\nHost: x\r\nContent-Length: 4\r\n"
           b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\nGET /private/secret.html HTTP/1.1\r\nHost: x\r\n\r\n")
    out = exchange(server, raw)
    assert out.startswith(b"HTTP/1.1 400")
    assert out.count(b"HTTP/1.1 ") == 1  # connection closed; the smuggled request never runs


@pytest.mark.parametrize("headers", [
    "Content-Length: 4, 5\r\n",
    "Content-Length: -1\r\n",
    "Transfer-Encoding: chunked, gzip\r\n",
    "Content-Length : 4\r\n",            # whitespace before the colon
    "X-Folded: a\r\n continued\r\n",     # obsolete line folding
])
def test_malformed_framing_is_rejected(server, headers):
    raw = f"POST /index.html HTTP/1.1\r\nHost: x\r\n{headers}Connection: close\r\n\r\n".encode()
    assert parse(exchange(server, raw))[0] == 400


def test_bad_chunk_size(server):
    status, _, _ = request(server, "PUT", "/private/bad.txt",
                           {"Authorization": BASIC, "Transfer-Encoding": "chunked"}, b"zz\r\nhello\r\n0\r\n\r\n")
    assert status == 400


def test_oversized_headers_get_431(server):
    raw = b"GET / HTTP/1.1\r\nHost: x\r\nX-Big: " + b"a" * 20000 + b"\r\n\r\n"
    assert parse(exchange(server, raw))[0] == 431


def test_oversized_body_gets_413(server):
    raw = b"PUT /private/big.txt HTTP/1.1\r\nHost: x\r\nContent-Length: 999999\r\n\r\n"
    assert parse(exchange(server, raw))[0] == 413


def test_put_without_length_gets_411(server):
    raw = b"PUT /private/x.txt HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"
    assert parse(exchange(server, raw))[0] == 411


def test_expect_100_continue(server):
    raw = (b"PUT /private/cont.txt HTTP/1.1\r\nHost: x\r\nConnection: close\r\nExpect: 100-continue\r\n"
           b"Authorization: " + BASIC.encode() + b"\r\nContent-Length: 2\r\n\r\nok")
    out = exchange(server, raw)
    assert out.startswith(b"HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 201")


# ---------------------------------------------------------------- conditional and range requests

def test_conditional_get(server):
    _, headers, _ = request(server, "GET", "/files/sample.txt")
    assert request(server, "GET", "/files/sample.txt", {"If-None-Match": headers["etag"]})[0] == 304
    assert request(server, "GET", "/files/sample.txt", {"If-Modified-Since": headers["last-modified"]})[0] == 304
    assert request(server, "GET", "/files/sample.txt", {"If-Match": '"nope"'})[0] == 412


def test_range_requests(server):
    full = (server["docroot"] / "files" / "sample.txt").read_bytes()
    status, headers, body = request(server, "GET", "/files/sample.txt", {"Range": "bytes=2-6"})
    assert status == 206 and body == full[2:7] and headers["content-range"] == f"bytes 2-6/{len(full)}"
    assert request(server, "GET", "/files/sample.txt", {"Range": "bytes=-5"})[2] == full[-5:]
    assert request(server, "GET", "/files/sample.txt", {"Range": "bytes=10-"})[2] == full[10:]
    assert request(server, "GET", "/files/sample.txt", {"Range": "bytes=9999-"})[0] == 416
    assert request(server, "GET", "/files/sample.txt", {"Range": "bytes=0-1, 4-5"})[0] == 200  # ignored


def test_concurrent_ranges_do_not_mix(server):
    full = (server["docroot"] / "files" / "sample.txt").read_bytes()
    errors = []

    def worker(i):
        start = i % 20
        status, _, body = request(server, "GET", "/files/sample.txt", {"Range": f"bytes={start}-{start + 9}"})
        if status != 206 or body != full[start:start + 10]:
            errors.append((i, status, body))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


# ---------------------------------------------------------------- directory listing

def test_listing_is_rendered_in_memory_and_escaped(server):
    before = set(os.listdir(server["docroot"] / "files"))
    status, headers, body = request(server, "GET", "/files/")
    html = dechunk(body)
    assert status == 200 and headers["transfer-encoding"] == "chunked"
    assert b"sample.txt" in html
    assert b"<em>bold" not in html and b"&lt;em&gt;bold&amp;amp.txt" in html
    assert str(server["docroot"]).encode() not in html  # no server paths leaked
    assert set(os.listdir(server["docroot"] / "files")) == before  # nothing written to disk


def test_listing_hides_protection_file(server):
    status, _, body = request(server, "GET", "/private/", {"Authorization": BASIC})
    assert status == 200 and b".protected" not in dechunk(body)


# ---------------------------------------------------------------- CGI

def test_cgi_runs_with_query_string(server):
    status, headers, body = request(server, "GET", "/cgi/hello.cgi?name=world")
    assert status == 200 and headers["content-type"] == "text/plain"
    assert b"method=GET" in body and b"query=name=world" in body


def test_cgi_file_name_is_not_run_through_a_shell(server):
    status, _, body = request(server, "GET", "/cgi/x%3Btouch%20PWNED.cgi")
    assert status == 200 and body == b"ran\n"
    assert not any("PWNED" in name for name in os.listdir(server["base"]))
    assert not (server["docroot"] / "cgi" / "PWNED").exists()


def test_cgi_does_not_see_server_secrets(server):
    script = server["docroot"] / "cgi" / "env.cgi"
    script.write_text("#!/bin/sh\nprintf 'Content-Type: text/plain\\n\\n'\nenv\n")
    script.chmod(0o755)
    _, _, body = request(server, "GET", "/cgi/env.cgi", {"Authorization": "Basic Zm9vOmJhcg=="})
    assert b"NONCE_SECRET" not in body and b"HTTP_AUTHORIZATION" not in body
    assert b"GATEWAY_INTERFACE=CGI/1.1" in body
