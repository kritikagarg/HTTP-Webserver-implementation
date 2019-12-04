import sys, os , os.path, re
import hashlib, base64
import imp_func, e_tag, unsafe
from time import time
#if 200 at end ... check authorisation

Auth=imp_func.main_dict['Auth']

docroot=imp_func.docroot
pk=imp_func.main_dict['priv_key']

nondic= dict(noncelist=[], snc=0)

def fgrep(file, wrd):
	val=None
	a_word=False
	if wrd=='ALLOW':
		a_word=True
		val=[]
	for line in file:
		if line.startswith(wrd):
			if not a_word:
				if "=" in line:
					k,val=line.split('=')
				elif ":" in line:
					val=line.split(':')[-1]
				break
			else:
				val.append(line.split('-')[1])			
	return val

#nonce= base64(time-stamp md5(time-stamp:ETag:private-key))
def gen_nonce(etag):
	ts=time()
	nonce=hashlib.md5(str.encode(f'{ts}:{etag}:{pk}')).hexdigest()
	k=f'{ts} {nonce}'
	nonce=base64.b64encode(k.encode()).decode()
	return nonce

#request_digest = md5(md5(A1):nonce:ncount:cnonce:qop:md5(A2))

def digest_auth(auth_val,file,wwwA, content, method, auth_dic):
	sc=401
	#print("Its Digest")
	try:
		etag = e_tag.gen_etag(content)			
		nonce=gen_nonce(etag)
		nondic["noncelist"].append(nonce)
		auth_dic["WWW-Authenticate"]=wwwA+ f', algorithm=MD5, qop="auth", nonce="{nonce}"'
		if auth_val:
			auth_val= auth_val[0][1]
			atype,val=auth_val.strip().split(' ',1)
			vd=parse_aval(val.split(', '))
			realm=fgrep(file,'realm')
			opaque=hashlib.md5(str.encode(f"{vd['uri']}:{pk}")).hexdigest()
			auth_dic["WWW-Authenticate"]=wwwA+ f', algorithm=MD5, qop="auth", nonce="{nonce}", opaque="{opaque}"'
			if realm.strip('\"') != vd['realm']:
				sc=401
				#print("realm is different")
			else:
				c_digest=vd['response']
				##print(c_digest)
				A1=fgrep(file, vd['username']) 
				A2=f"{method}:{vd['uri']}"
				A2=hashlib.md5(str.encode(A2)).hexdigest()
				cnonce=vd['cnonce']
				##print(vd['nonce'])
				##print(nondic["noncelist"])
				if vd['nonce'] in nondic["noncelist"]:
					nondic["snc"]=+1

				qop=vd['qop']
				nc=vd['nc']
				snc=nondic["snc"]
				#print(nc)
				snc=f'0000000{snc}'
				#print(snc)

				if snc==nc:
					s_digest=f"{A1}:{vd['nonce']}:{snc}:{cnonce}:{qop}:{A2}"
					s_digest=hashlib.md5(str.encode(s_digest)).hexdigest()
					if s_digest==c_digest:
						#print("Digest auth matched")
						sc=200
						del auth_dic["WWW-Authenticate"]
						A2=f":{vd['uri']}"
						A2=hashlib.md5(str.encode(A2)).hexdigest()
						rspauth=f"{A1}:{vd['nonce']}:{nc}:{cnonce}:{qop}:{A2}"
						rspauth=hashlib.md5(str.encode(rspauth)).hexdigest()
						op=f'Digest rspauth="{rspauth}", cnonce="{cnonce}", nc={snc}, qop={qop}'
						auth_dic["Authentication-Info"]= op
					##print(1)
		else:
			if "Authentication-Info" in auth_dic:
				del auth_dic["Authentication-Info"]
	except FileNotFoundError as e:
		sc=401 #protected and does not exist
		auth_dic["WWW-Authenticate"]=wwwA+ f', algorithm=MD5, qop="auth"'
	return sc, auth_dic


#__________________________________________________________
def basic_auth(auth_val,file,wwwA, auth_dic):
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
				del auth_dic["WWW-Authenticate"]
	return sc, auth_dic


def check_atype(auth_val, file, content, method, auth_dic):
	#print("Checking auth type")
	sc=401
	atype=fgrep(file, 'authorization-type')
	wwwA=atype
	realm=fgrep(file,'realm')
	if realm:
		wwwA=wwwA+f' realm={realm}'	

	if atype=='Basic':
		sc, auth_dic=basic_auth(auth_val,file,wwwA, auth_dic)
	elif atype=='Digest':
		sc, auth_dic=digest_auth(auth_val,file, wwwA, content, method, auth_dic)
	if sc==200 and method=='PUT':
		sc=201
	return sc, auth_dic	


def parse_aval(s):
	dic={}	
	for line in s:
			k,v=line.split('=')
			dic[k]=v.strip('\"')
	return dic

def check_protection(f_path, method, content, client_payload, auth_val):
	#print(method)
	sc=200
	auth_dic={}
	allow=['GET', 'HEAD', 'TRACE', 'OPTIONS', 'POST']
	while True:
		fprotect=os.path.join(f_path,Auth)
		protected=os.path.exists(fprotect)
		if protected:
			#print("Protected")
			sc=401
			file=open(fprotect, 'r').read().splitlines()
			ml=fgrep(file, 'ALLOW')
			allow=set(allow+ml)
			if method in allow:
				if method =='DELETE' : #checking if delete and put are allowed
					sc=200
				else:
					if method =='PUT':
						unsafe.create_file(content, client_payload)

					sc, auth_dic=check_atype(auth_val, file, content, method, auth_dic)
			else:
				sc=405

			break
		else:
			try:
				if not os.path.samefile(f_path, docroot):
					f_path=os.path.join(f_path,'../')
				else:
					break
			except FileNotFoundError as e:
				sc=404   #not protected and does not exist
				break
	return sc, allow, auth_dic

def check_authorised(content, method, client_payload, auth_val=None):
	f_name=os.path.basename(content)
	f_path=content.strip(f_name)	
	sc, allow, auth_dic=check_protection(f_path, method, content, client_payload, auth_val)
	return sc, allow, auth_dic