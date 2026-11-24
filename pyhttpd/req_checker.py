import os
import re

from . import imp_func
from . import path_checker, conditional, partial_check, authorize, unsafe, cgi_file

main_dict = imp_func.main_dict


def check_headers(req):
    # Unknown request headers are ignored, as RFC 9110 requires; a fixed
    # allow-list would reject ordinary browsers. HTTP/1.1 needs exactly one valid Host.
    hosts = [value for name, value in req[1:] if name == "host"]
    if len(hosts) != 1:
        return 400
    if not re.match(r"^[\w\.\-:\[\]]*$", hosts[0]):
        return 400
    return 200


def check_version(req):
    if req[0][2].strip() == "HTTP/1.1":
        return check_headers(req)
    return 505


def check_method(req):
    m = req[0][0]
    if not (m.isalpha() and m.isupper()):
        return 400
    if m not in main_dict['methods']:
        return 501
    return check_version(req)


def check_request(req, client_payload):
    content, c_path = imp_func.get_content(req)  # raises imp_func.Forbidden outside the docroot
    sc = check_method(req)
    method = req[0][0]
    loc = None
    ndic, auth_dic = None, {}
    allow = []
    if sc != 200:
        return sc, allow, auth_dic, loc, ndic, content
    if os.path.basename(content) == imp_func.protect_file:
        return 403, allow, auth_dic, loc, ndic, content  # never serve or overwrite password files
    auth_val = imp_func.get_reqheader_value("authorization", req)
    if len(auth_val) > 1:
        return 400, allow, auth_dic, loc, ndic, content
    sc, allow, auth_dic = authorize.check_authorised(content, method, client_payload, auth_val, req[0][1])
    if sc == 200:
        if method in {'DELETE', 'PUT'}:
            sc = unsafe.unsafe_method_handler(req, client_payload, content)
        else:
            sc, loc, ndic, content = path_checker.path_check(req)
            if sc == 200 and method in {'GET', 'HEAD'} and not cgi_file.is_cgi(content):
                sc = conditional.check_conditional_requests(req, content)
                if sc == 200:
                    sc = partial_check.check_partial(req)
    return sc, allow, auth_dic, loc, ndic, content
