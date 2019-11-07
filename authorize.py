import sys, os , os.path, re
import hashlib, base64
import imp_func, e_tag
from time import time
#if 200 at end ... check authorisation

Auth=imp_func.main_dict['Auth']
docroot=imp_func.docroot
auth_dic={}
pk=imp_func.main_dict['priv_key']

def fgrep(file, wrd):
	val=None
	for line in file:
		if line.startswith(wrd):
			if "=" in line:
				k,val=line.split('=')
			elif ":" in line:
				val=line.split(':')[-1]
			break
	return val

#nonce= base64(time-stamp md5(time-stamp:ETag:private-key))
def gen_nonce(etag):
	ts=time()
	nonce=hashlib.md5(str.encode(f'{ts}:{etag}:{pk}')).hexdigest()
	k=f'{ts} {nonce}'
	nonce=base64.b64encode(k.encode()).decode()
	return nonce

#request_digest = md5(md5(A1):nonce:ncount:cnonce:qop:md5(A2))

def digest_auth(auth_val,file,wwwA, content, method):
	sc=401
	etag = e_tag.gen_etag(content)
	nonce=gen_nonce(etag)
	auth_dic["WWW-Authenticate"]=wwwA+ f', algorithm=MD5, qop="auth", nonce="{nonce}"'
	if auth_val:
		auth_val= auth_val[0][1]
		atype,val=auth_val.strip().split(' ',1)
		vd=parse_aval(val.split(', '))
		realm=fgrep(file,'realm')
		if realm.strip('\"') != vd['realm']:
			sc=401
		else:
			c_digest=vd['response']
			print(c_digest)
			A1=fgrep(file, vd['username']) 
			A2=f"{method}:{vd['uri']}"
			A2=hashlib.md5(str.encode(A2)).hexdigest()
			cnonce=vd['cnonce']
			qop=vd['qop']
			nc=vd['nc']
			s_digest=f"{A1}:{vd['nonce']}:{nc}:{cnonce}:{qop}:{A2}"
			s_digest=hashlib.md5(str.encode(s_digest)).hexdigest()
			if s_digest==c_digest:
				sc=200
				A2=f":{vd['uri']}"
				A2=hashlib.md5(str.encode(A2)).hexdigest()
				rspauth=f"{A1}:{vd['nonce']}:{nc}:{cnonce}:{qop}:{A2}"
				rspauth=hashlib.md5(str.encode(rspauth)).hexdigest()
				op=f'Digest rspauth="{rspauth}", cnonce="{cnonce}", nc={nc}, qop={qop}'
				auth_dic["Authentication-Info"]= op
				print(1)
	else:
		if "Authentication-Info" in auth_dic:
			del auth_dic["Authentication-Info"]
	return sc


#__________________________________________________________
def basic_auth(auth_val,file,wwwA):
	sc=401
	auth_dic["WWW-Authenticate"]=wwwA
	if auth_val:
		auth_val= auth_val[0][1]
		atype,val=auth_val.strip().split(' ',1)
		usr,pswd=(base64.b64decode(val)).decode("utf-8").split(':')
		pswd=hashlib.md5(str.encode(pswd)).hexdigest()
		Fpswd=fgrep(file, usr)
		if Fpswd:  
			if Fpswd==pswd:
				sc=200
	return sc


def check_atype(auth_val, file, content, method):
	sc=401
	atype=fgrep(file, 'authorization-type')
	wwwA=atype
	realm=fgrep(file,'realm')
	if realm:
		wwwA=wwwA+f' realm={realm}'	

	if atype=='Basic':
		sc=basic_auth(auth_val,file,wwwA)
	elif atype=='Digest':
		sc=digest_auth(auth_val,file, wwwA, content, method)
	return sc	


def parse_aval(s):
	dic={}	
	for line in s:
			k,v=line.split('=')
			dic[k]=v.strip('\"')
	return dic

def check_protection(f_path, method, content, auth_val):
	sc=200
	while True:
		fprotect=os.path.join(f_path,Auth)
		protected=os.path.exists(fprotect)
		if protected:
			sc=401
			print(f"filefound at {f_path}")
			file=open(fprotect, 'r').read().splitlines()
			sc=check_atype(auth_val, file, content, method)
			break
		else:
			try:
				if not os.path.samefile(f_path, docroot):
					f_path=os.path.join(f_path,'../')
				else:
					break
			except FileNotFoundError as e:
				sc=404
				break
	return sc

def check_authorised(content, method, auth_val=None):
	f_name=os.path.basename(content)
	f_path=content.strip(f_name)	
	sc=check_protection(f_path, method, content, auth_val)
	return sc