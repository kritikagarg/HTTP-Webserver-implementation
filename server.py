#!/usr/bin/env python3
"""Threaded HTTP/1.1 server: one thread per connection, persistent and pipelined requests."""
import os
import socket
import sys
import threading
import traceback

import parser, req_checker, imp_func, response

HOST = '0.0.0.0'
PORT = 8080
if len(sys.argv) > 1:
    HOST = sys.argv[1]
if len(sys.argv) > 2:
    PORT = int(sys.argv[2])

TIMEOUT = float(os.getenv("KEEPALIVE_TIMEOUT", imp_func.main_dict['timeout']))


def req_handler(parsed_dic, orignal_msg, meta):
    req = parsed_dic["req"]
    connection = 'close'
    allow, loc, ndic, content = None, None, None, None
    auth_dic = {}
    if parsed_dic["bad_req"]:
        sc = 400
    else:
        connection = imp_func.connect(req)
        try:
            sc, allow, auth_dic, loc, ndic, content = req_checker.check_request(
                req, meta.get("client_payload"))
        except imp_func.Forbidden:
            sc = 403
    res, sc = response.response_handler(sc, req, orignal_msg, connection, allow, loc,
                                        ndic, content, auth_dic, meta)
    return res, connection, sc


def read_body(reader, req, conn):
    kind, n = parser.body_length(req)
    expects_continue = any(name == "expect" and value.lower() == "100-continue"
                           for name, value in req[1:])
    if req[0][0] == "PUT" and kind is None:
        raise parser.HTTPError(411)  # PUT needs a framed body
    if kind and expects_continue:
        conn.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
    if kind == "chunked":
        return reader.read_chunked()
    if kind == "length":
        return reader.read_exact(n)
    return None


def client_handler(conn, addr, logfile):
    reader = parser.Reader(conn)
    conn.settimeout(TIMEOUT)
    try:
        while True:
            try:
                head = reader.read_head()
                parsed_dic = parser.request_parser(head)
                req = parsed_dic["req"]
                client_payload = None
                if not parsed_dic["bad_req"]:
                    client_payload = read_body(reader, req, conn)
            except parser.ConnectionClosed:
                break
            except socket.timeout:
                conn.sendall(response.res_object({'Content-Length': '0', 'Connection': 'close'},
                                                  408, encode=True))
                break
            except parser.HTTPError as e:
                # The message boundary is unknown, so answer and close the connection.
                conn.sendall(response.error_response(e.status))
                imp_func.log_dump(addr[0], ["-"], e.status, {}, logfile=logfile)
                break

            meta = {"remote_addr": addr[0], "client_payload": client_payload}
            try:
                res, connection, sc = req_handler(parsed_dic, head + b"\r\n\r\n", meta)
            except Exception:
                traceback.print_exc()
                res, connection, sc = response.error_response(500), 'close', 500
            conn.sendall(res)
            imp_func.log_dump(addr[0], req, sc, meta, logfile=logfile)

            if connection.lower() == 'close':
                break
    except OSError:
        pass  # client reset or went away
    finally:
        conn.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Listening on {HOST}:{PORT} (docroot {imp_func.docroot})", flush=True)
    os.makedirs(os.path.dirname(imp_func.log_path), exist_ok=True)
    lfile = open(imp_func.log_path, 'a', buffering=1)
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=client_handler, args=(conn, addr, lfile), daemon=True).start()
    except KeyboardInterrupt:
        print("Server socket closed")
    finally:
        s.close()
        lfile.close()


if __name__ == "__main__":
    main()
