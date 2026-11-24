"""HTTP Basic and Digest authentication driven by per-directory protection files.

Protection file format (one per directory, applies to that directory and below):

    authorization-type=Basic | Digest
    realm="Some Realm"
    ALLOW-PUT                      # optional: permit unsafe methods here
    ALLOW-DELETE
    user:md5(password)             # Basic
    user:realm:md5(user:realm:pw)  # Digest (HA1)
"""
import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
import threading
from time import time

from . import e_tag
from . import imp_func

docroot = imp_func.docroot
PROTECT_FILE = imp_func.protect_file

# Secret mixed into nonces and opaque values. Set NONCE_SECRET to keep nonces
# valid across restarts; otherwise a random secret is generated per process.
pk = os.getenv("NONCE_SECRET") or secrets.token_hex(32)

DEFAULT_ALLOW = ['GET', 'HEAD', 'TRACE', 'OPTIONS', 'POST']


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


class NonceStore:
    """Issued Digest nonces and the highest nonce-count seen for each.

    Shared by all connection threads, so access is locked. Nonces expire, and
    the store is bounded so it can't grow without limit.
    """

    def __init__(self, ttl=300, max_size=10000):
        self.ttl, self.max_size = ttl, max_size
        self._lock = threading.Lock()
        self._nonces = {}  # nonce -> [issued_at, last_nc]

    def issue(self, etag):
        ts = time()
        digest = md5(f'{ts}:{etag}:{pk}')
        nonce = base64.b64encode(f'{ts} {digest}'.encode()).decode()
        with self._lock:
            self._prune(ts)
            self._nonces[nonce] = [ts, 0]
        return nonce

    def _prune(self, now):
        for n in [n for n, (t, _) in self._nonces.items() if now - t > self.ttl]:
            del self._nonces[n]
        while len(self._nonces) >= self.max_size:
            del self._nonces[next(iter(self._nonces))]

    def is_valid(self, nonce):
        with self._lock:
            entry = self._nonces.get(nonce)
            return bool(entry) and time() - entry[0] <= self.ttl

    def use(self, nonce, nc_hex):
        """Accept nc only if it's higher than any count already used (stops replays)."""
        try:
            nc = int(nc_hex, 16)
        except (TypeError, ValueError):
            return False
        with self._lock:
            entry = self._nonces.get(nonce)
            if not entry or time() - entry[0] > self.ttl or nc <= entry[1]:
                return False
            entry[1] = nc
            return True


nonces = NonceStore()


def fgrep(file, wrd):
    """Value of a 'key=value' directive, or the list of ALLOW-* methods."""
    if wrd == 'ALLOW':
        return [line.split('-', 1)[1].strip() for line in file if line.startswith('ALLOW-')]
    for line in file:
        if line.startswith(wrd):
            if "=" in line:
                return line.split('=', 1)[1].strip()
            return line.split(':')[-1].strip()
    return None


def find_user(file, username):
    """Stored hash for an exact username match (not a prefix match)."""
    for line in file:
        if line.startswith('#') or ':' not in line:
            continue
        if line.split(':', 1)[0] == username:
            return line.rsplit(':', 1)[1].strip()
    return None


def parse_aval(s):
    """Parse Digest auth-params, handling quoted values that contain ',' or '='."""
    return {k: (q if q else v) for k, q, v in
            re.findall(r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^,\s]*))', s)}


def digest_auth(auth_val, file, wwwA, content, method, auth_dic, request_uri):
    def challenge(opaque=None):
        nonce = nonces.issue(e_tag.gen_etag(content) if os.path.isfile(content) else "")
        value = wwwA + f', algorithm=MD5, qop="auth", nonce="{nonce}"'
        if opaque:
            value += f', opaque="{opaque}"'
        auth_dic["WWW-Authenticate"] = value
        return 401, auth_dic

    if not auth_val:
        return challenge()
    atype, _, val = auth_val[0][1].strip().partition(' ')
    vd = parse_aval(val)
    if atype.lower() != 'digest' or not {'username', 'realm', 'nonce', 'uri', 'response'} <= vd.keys():
        return challenge()
    opaque = md5(f"{vd['uri']}:{pk}")
    realm = (fgrep(file, 'realm') or '').strip('"')
    ha1 = find_user(file, vd['username'])
    if realm != vd['realm'] or ha1 is None or not nonces.is_valid(vd['nonce']):
        return challenge(opaque)
    if vd['uri'] != request_uri:
        return challenge(opaque)  # credentials were computed for a different URI

    qop, nc, cnonce = vd.get('qop', ''), vd.get('nc', ''), vd.get('cnonce', '')
    ha2 = md5(f"{method}:{vd['uri']}")
    expected = md5(f"{ha1}:{vd['nonce']}:{nc}:{cnonce}:{qop}:{ha2}")
    if not hmac.compare_digest(expected, vd['response']):
        return challenge(opaque)
    if not nonces.use(vd['nonce'], nc):
        return challenge(opaque)  # replayed nonce-count

    rspauth = md5(f"{ha1}:{vd['nonce']}:{nc}:{cnonce}:{qop}:{md5(':' + vd['uri'])}")
    auth_dic.pop("WWW-Authenticate", None)
    auth_dic["Authentication-Info"] = f'rspauth="{rspauth}", cnonce="{cnonce}", nc={nc}, qop={qop}'
    return 200, auth_dic


def basic_auth(auth_val, file, wwwA, auth_dic):
    auth_dic["WWW-Authenticate"] = wwwA
    if not auth_val:
        return 401, auth_dic
    try:
        atype, val = auth_val[0][1].strip().split(' ', 1)
        usr, pswd = base64.b64decode(val, validate=True).decode("utf-8").split(':', 1)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return 401, auth_dic
    stored = find_user(file, usr)
    if atype.lower() == 'basic' and stored and hmac.compare_digest(stored, md5(pswd)):
        del auth_dic["WWW-Authenticate"]
        return 200, auth_dic
    return 401, auth_dic


def check_atype(auth_val, file, content, method, auth_dic, request_uri):
    atype = fgrep(file, 'authorization-type')
    realm = fgrep(file, 'realm')
    wwwA = atype or ''
    if realm:
        wwwA = wwwA + f' realm={realm}'
    if atype == 'Basic':
        return basic_auth(auth_val, file, wwwA, auth_dic)
    if atype == 'Digest':
        return digest_auth(auth_val, file, wwwA, content, method, auth_dic, request_uri)
    return 401, auth_dic


def find_protection_file(f_path):
    """Walk from f_path up to the document root and return the nearest protection file.

    The walk never leaves the document root, so it always terminates.
    """
    path = os.path.realpath(f_path)
    while path == docroot or path.startswith(docroot + os.sep):
        candidate = os.path.join(path, PROTECT_FILE)
        if os.path.isfile(candidate):
            return candidate
        if path == docroot:
            break
        path = os.path.dirname(path)
    return None


def check_protection(f_path, method, content, client_payload, auth_val, request_uri):
    auth_dic = {}
    allow = list(DEFAULT_ALLOW)
    if not os.path.isdir(f_path):
        return 404, allow, auth_dic  # not protected and does not exist
    fprotect = find_protection_file(f_path)
    if fprotect is None:
        # PUT and DELETE are only allowed where a protection file grants them.
        sc = 405 if method in {'PUT', 'DELETE'} else 200
        return sc, allow, auth_dic
    with open(fprotect, 'r') as f:
        file = f.read().splitlines()
    allow += [m for m in fgrep(file, 'ALLOW') if m not in allow]
    if method not in allow:
        return 405, allow, auth_dic
    # Every method, including PUT and DELETE, must authenticate before it runs.
    sc, auth_dic = check_atype(auth_val, file, content, method, auth_dic, request_uri)
    return sc, allow, auth_dic


def check_authorised(content, method, client_payload, auth_val=None, request_uri=None):
    f_path = os.path.dirname(content)
    return check_protection(f_path, method, content, client_payload, auth_val, request_uri)
