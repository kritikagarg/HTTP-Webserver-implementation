import os
import time
from wsgiref.handlers import format_date_time

from . import imp_func, res_functions, e_tag, partial_check, fs, cgi_file

Server = "kitkat.2.0"

main_dict = imp_func.main_dict
status_code_dic = main_dict['status_code']
CHUNK_SIZE = 8192

with open(os.path.join(imp_func.BASE_DIR, "templates", "meta_list.html"), 'r') as f:
    ERROR_TEMPLATE = f.read()


def res_object(res_headers, sc, encode=False, reason=None):
    status = f"HTTP/1.1 {sc} {reason or status_code_dic.get(sc, 'Unknown')}"
    res = status + '\r\n'
    res += 'Date: ' + format_date_time(time.time()) + '\r\n'  # current time, per response
    res += 'Server: ' + Server + '\r\n'
    for k, v in res_headers.items():
        res += f"{k}: {v}\r\n"
    res += '\r\n'
    if encode:
        res = res.encode()
    return res


def chunking(payload):
    """Encode bytes with chunked transfer coding (sizes are byte counts)."""
    out = []
    for i in range(0, len(payload), CHUNK_SIZE):
        chunk = payload[i:i + CHUNK_SIZE]
        out.append(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
    out.append(b"0\r\n\r\n")
    return b"".join(out)


def error_page(sc, extra=""):
    msg = ERROR_TEMPLATE.replace('#SC#', str(sc))
    msg = msg.replace('#SM#', status_code_dic.get(sc, ''))
    msg = msg.replace('----', extra)
    return msg.encode()


def error_response(sc, connection='close', extra_headers=None):
    """Standalone error response, used when the request can't be parsed or framed."""
    payload = error_page(sc)
    headers = {'Content-Type': 'text/html', 'Content-Length': len(payload), 'Connection': connection}
    headers.update(extra_headers or {})
    return res_object(headers, sc, encode=True) + payload


def cgi_response(req, content, connection, meta):
    method = req[0][0]
    try:
        sc, reason, headers, body = cgi_file.run_cgi(
            content, req, meta.get('client_payload'), meta.get('remote_addr'))
    except (cgi_file.CGIError, ValueError):
        meta['content_length'] = '-'
        return error_response(500, connection), 500
    headers.update({'Content-Length': len(body), 'Connection': connection})
    meta['content_length'] = len(body)
    res = res_object(headers, sc, encode=True, reason=reason)
    if method != 'HEAD':
        res += body
    return res, sc


def response_handler(sc, req, orignal_msg, connection, allow, loc, ndic, content, auth_dic, meta=None):
    """Build the full response. `meta` is a per-request dict: it carries the client
    address and body in, and the logged content length out (no shared globals)."""
    if meta is None:
        meta = {}
    method = req[0][0]
    content_length = '0'
    payload = None
    res_headers = {}
    dynamic = False
    content_type = 'text/html'
    variants_html = ndic.pop('_variants_html', '') if ndic else ''

    if sc == 200 and method in {'GET', 'HEAD', 'POST'} and content and cgi_file.is_cgi(content):
        res, sc = cgi_response(req, content, connection, meta)
        return res, sc

    if sc // 100 == 2 and method != 'DELETE':
        content1, c_path = imp_func.get_content(req)
        comp, extension, lang, charset = res_functions.find_ext(content)

        if method != 'TRACE':
            last_modified = format_date_time(fs.mtime(content))
            etag = e_tag.gen_etag(content)
            res_headers.update({'Last-Modified': last_modified, 'ETag': etag})

        if content1 != content:
            res_headers.update({'Content-Location': content.replace(imp_func.docroot, '')})

        if sc == 200:
            payload, content_length = res_functions.content_attribute(method, content, orignal_msg)

        if sc == 206:
            payload, content_length, content_range, ok = partial_check.partial_content(method, content, req)
            if not ok:
                sc = 416
                payload = None
            res_headers.update({'Content-Range': content_range})

        if lang:
            res_headers.update({'Content-Language': lang})
        if comp:
            res_headers.update({'Content-Encoding': comp})

        content_type = res_functions.get_content_type(extension, charset)
        res_headers.update({'Content-Length': content_length, 'Content-Type': content_type})
        if fs.is_listing(content) and method != 'TRACE':
            content_length = '-'
            dynamic = True

    if sc // 100 != 2:
        if sc != 304:
            dynamic = True
            payload = error_page(sc, variants_html if sc in {300, 406} else '')
            content_length = len(payload)

        if sc in {301, 302}:
            res_headers.update({'Location': loc})

    res_headers.update(auth_dic or {})

    if method == "TRACE":
        content_type = "message/http"

    if (method == "OPTIONS" or sc == 405) and allow:
        res_headers["Allow"] = ", ".join(allow)

    if ndic:
        res_headers.update(ndic)

    res_headers.update({'Content-Type': content_type, 'Connection': connection})

    if method == "DELETE" and sc == 200:
        payload = b"<html>\r\n<body>\r\n<h1>File deleted.</h1>\r\n</body>\r\n</html>"
        res_headers = {'Content-Type': 'text/html', 'Connection': connection}
        dynamic = True

    res_headers.update({'Content-Length': content_length})

    if dynamic:
        res_headers.update({'Transfer-Encoding': 'chunked'})
        res_headers.pop('Content-Length')
        if method != 'HEAD':
            payload = chunking(payload or b"")
    elif method == 'GET' and sc in {200, 206}:
        res_headers.update({'Accept-Ranges': 'bytes'})

    res = res_object(res_headers, sc).encode()
    meta["content_length"] = content_length
    if payload and method != 'HEAD':
        res = res + payload
    return res, sc
