"""CGI/1.1 execution (RFC 3875).

Scripts run directly with subprocess (no shell), so characters in a file name
or URL can't be interpreted as shell commands. They get a minimal environment
that doesn't include the server's own environment variables or secrets.
"""
import os
import subprocess
from urllib.parse import urlparse, unquote

CGI_TIMEOUT = float(os.getenv("CGI_TIMEOUT", "10"))
SERVER_SOFTWARE = "kitkat.2.0"


class CGIError(Exception):
    pass


def is_cgi(content):
    return content.endswith(".cgi") and os.path.isfile(content)


def build_env(content, req, body, remote_addr):
    method, target, version = req[0]
    url = urlparse(target)
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "GATEWAY_INTERFACE": "CGI/1.1",
        "SERVER_PROTOCOL": version,
        "SERVER_SOFTWARE": SERVER_SOFTWARE,
        "REQUEST_METHOD": method,
        "QUERY_STRING": url.query,
        "SCRIPT_NAME": unquote(url.path),
        "SCRIPT_FILENAME": content,
        "REMOTE_ADDR": remote_addr or "",
    }
    if body:
        env["CONTENT_LENGTH"] = str(len(body))
    for name, value in req[1:]:
        if name == "content-type":
            env["CONTENT_TYPE"] = value
        elif name == "host":
            host, _, port = value.partition(":")
            env["SERVER_NAME"] = host
            env["SERVER_PORT"] = port or "80"
            env["HTTP_HOST"] = value
        elif name in ("authorization", "proxy"):
            # Don't pass credentials to scripts; skip Proxy to avoid "httpoxy".
            continue
        else:
            env["HTTP_" + name.upper().replace("-", "_")] = value
    return env


def parse_output(out):
    """Split CGI output into (status, reason, headers, body)."""
    cut = [i for i in (out.find(b"\r\n\r\n"), out.find(b"\n\n")) if i != -1]
    if not cut:
        raise CGIError("no header/body separator in CGI output")
    i = min(cut)
    sep = 4 if out[i:i + 4] == b"\r\n\r\n" else 2
    head, body = out[:i], out[i + sep:]
    headers, status, reason = {}, None, None
    for line in head.decode("latin-1").splitlines():
        if not line.strip():
            continue
        name, colon, value = line.partition(":")
        if not colon:
            raise CGIError(f"bad CGI header line: {line!r}")
        name, value = name.strip(), value.strip()
        if name.lower() == "status":
            code, _, reason = value.partition(" ")
            status = int(code)
        elif name.lower() == "content-type":
            headers["Content-Type"] = value
        elif name.lower() == "location":
            headers["Location"] = value
        else:
            headers[name] = value
    if status is None:
        status = 302 if "Location" in headers else 200
    if "Content-Type" not in headers and "Location" not in headers and status == 200:
        raise CGIError("CGI response has no Content-Type")
    return status, reason or None, headers, body


def run_cgi(content, req, body, remote_addr):
    try:
        proc = subprocess.run(
            [content],
            input=body or b"",
            env=build_env(content, req, body, remote_addr),
            cwd=os.path.dirname(content),
            capture_output=True,
            timeout=CGI_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CGIError(str(e)) from e
    return parse_output(proc.stdout)
