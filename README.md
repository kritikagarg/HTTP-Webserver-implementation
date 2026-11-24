# HTTP/1.1 Web Server in Python

An HTTP/1.1 server written from scratch on raw TCP sockets, without a web
framework. It implements the protocol directly: message framing, persistent and
pipelined connections, conditional and range requests, content negotiation,
authentication and CGI.

It started as my project for ODU's Web Server Design course and has since been
reworked for security and standards conformance.

## Features

- **Methods:** GET, HEAD, POST, OPTIONS, TRACE, PUT, DELETE
- **Connections:** persistent (keep-alive) and pipelined requests, idle timeout (408), one thread per connection
- **Message framing (RFC 9112):** exact Content-Length bodies, chunked request bodies, `Expect: 100-continue`, chunked responses for generated pages
- **Conditional requests:** strong ETags, Last-Modified, If-Match, If-None-Match, If-Modified-Since, If-Unmodified-Since (304/412)
- **Range requests:** single byte ranges, including open-ended and suffix ranges (206/416)
- **Content negotiation:** variants by media type, language, charset and encoding (`Accept-*`, 300/406)
- **Authentication:** HTTP Basic and Digest (MD5, `qop=auth`) driven by per-directory protection files
- **Redirects:** regex rules in `redirect.yaml` (301/302)
- **CGI/1.1:** `.cgi` scripts with the standard environment, `Status` and `Location` headers
- **Directory listings** and a Common Log Format access log (also served at `/.well-known/access.log`)

## Security hardening

- Request paths are resolved (including `..` and symlinks) and refused with 403 if they land outside the document root.
- PUT and DELETE are only allowed in directories whose protection file grants them (`ALLOW-PUT`, `ALLOW-DELETE`), and always require authentication.
- Requests with both `Content-Length` and `Transfer-Encoding`, conflicting lengths, obsolete line folding or whitespace before a header colon are rejected, which blocks HTTP request smuggling.
- Header and body sizes are capped (431/413).
- CGI scripts run without a shell and get a minimal environment that never includes the server's secrets or the client's credentials.
- Protection files are never served or listed. Directory listings escape file names.
- Digest nonces expire, and a nonce-count can't be reused (replay protection).

## Running

```bash
pip install -r requirements.txt
python -m pyhttpd 127.0.0.1 8080       # serves ./www by default
```

Or with Docker:

```bash
docker build -t pyhttpd .
docker run -p 8080:8080 pyhttpd
```

Then open <http://localhost:8080/>. The sample site in `www/` shows a directory
listing, negotiation, a redirect, a CGI script, and a Basic-auth area
(`/private/`, user `demo`, password `demo`; change it before deploying).

## Configuration

| Environment variable | Default | Purpose |
|---|---|---|
| `DOCROOT` | `./www` | Directory to serve |
| `LOG_DIR` | `./logs` | Access log directory |
| `PROTECT_FILE` | `.protected` | Name of per-directory protection files |
| `NONCE_SECRET` | random per process | Secret for Digest nonces; set it to keep nonces valid across restarts |
| `KEEPALIVE_TIMEOUT` | `5` | Seconds to wait on an idle connection |
| `MAX_HEADER_BYTES` | `16384` | Header block size limit (431 above it) |
| `MAX_BODY_BYTES` | `10485760` | Request body size limit (413 above it) |
| `CGI_TIMEOUT` | `10` | Seconds before a CGI script is stopped |
| `CONFIG_DIR` | `pyhttpd/config` | Directory containing `check.yaml` and `redirect.yaml` |

`pyhttpd/config/check.yaml` holds protocol data (status codes, MIME types,
supported methods), and `pyhttpd/config/redirect.yaml` holds redirect rules. Set
`CONFIG_DIR` to use your own copies of both files.

### Protection files

A protection file applies to its directory and everything below it:

```
authorization-type=Basic
realm="Demo Area"
ALLOW-PUT
ALLOW-DELETE
demo:fe01ce2a7fbac8fafaed7c982a04e229        # user:md5(password)
```

For Digest, use `authorization-type=Digest` and lines of the form
`user:realm:md5(user:realm:password)`.

## Tests

```bash
python -m pytest tests/
```

The suite starts the server on a free port and talks to it over raw sockets. It
covers normal behavior (conditional, range, negotiation, CGI, auth) and the
security cases above: path traversal, unauthenticated writes, request smuggling,
oversized messages, slow clients, pipelining, concurrent range requests and
Digest replays.

## Project layout

```
pyhttpd/                 the server package (run with: python -m pyhttpd)
├── __main__.py          entry point
├── server.py            socket server, connection loop, keep-alive and pipelining
├── parser.py            message framing and request parsing
├── req_checker.py       validates the request and runs the checks in order
├── imp_func.py          configuration, path resolution, logging
├── fs.py                file access, including in-memory directory listings
├── authorize.py         protection files, Basic and Digest auth
├── path_checker.py      redirects and existence checks
├── nego.py              content negotiation
├── conditional.py       conditional requests
├── e_tag.py             ETags
├── partial_check.py     range requests
├── unsafe.py            PUT and DELETE
├── cgi_file.py          CGI execution
├── response.py          building responses
├── res_functions.py     response helpers (MIME types, content attributes)
├── direc_list.py        directory listing HTML
├── config/              check.yaml (protocol data), redirect.yaml (redirect rules)
└── templates/           HTML templates for listings and error pages
www/                     sample document root
tests/                   end-to-end test suite
logs/                    access log (created at runtime)
Dockerfile, requirements.txt
```
