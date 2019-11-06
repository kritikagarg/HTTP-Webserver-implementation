import sys, os , os.path, re
import hashlib, base64
import imp_func
#if 200 at end ... check authorisation

Auth=imp_func.main_dict['Auth']
docroot=imp_func.docroot
auth_dic={}
pk=imp_func.main_dict['priv_key']




def fgrep(file, wrd):
	val=None
	print(wrd)
	for line in file:
		if line.startswith(wrd):
			print("found")
			if "=" in line:
				k,val=line.split('=')
			elif ":" in line:
				val=line.split(':')[-1]
			break
	return val


#____________________________________________________________




# def gen_server_digest(vd,file, method):
# 	A1=fgrep(file, vd['username'])
# 	A2=f"{method}:{vd['uri']}"
# 	print(A1)
# 	print(A2)





#request_digest = md5(md5(A1):nonce:ncount:cnonce:qop:md5(A2))

def digest_auth(auth_val,file,wwwA, method):
	sc=401
	nonce=500 #gen_nonce()
	auth_dic["WWW-Authenticate"]=wwwA+ f', algorithm=MD5, qop="auth", nonce="{nonce}"'
	if auth_val:
		auth_val= auth_val[0][1]
		atype,val=auth_val.strip().split(' ',1)
		vd=parse_aval(val.split(', '))
		realm=fgrep(file,'realm')
		print(realm)
		print(vd['realm'])
		if realm.strip('\"') != vd['realm']:
			sc=401
		else:
			c_digest=vd['response']
			print(c_digest)
			A1=fgrep(file, vd['username']) 
			A2=f"{method}:{vd['uri']}"
			A2=hashlib.md5(str.encode(A2)).hexdigest()
			s_digest=f"{A1}:{vd['nonce']}:{vd['nc']}:{vd['cnonce']}:{vd['qop']}:{A2}"
			s_digest=hashlib.md5(str.encode(s_digest)).hexdigest()
			if s_digest==c_digest:
				sc=200
				auth_dic["Authentication-Info"]=f"Digest {val}" #cal new cnonce,
				print(1)
	else:
		print(2)
		if "Authentication-Info" in auth_dic:
			print(3)
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


def check_atype(auth_val, file, method):
	sc=401
	atype=fgrep(file, 'authorization-type')
	wwwA=atype
	realm=fgrep(file,'realm')
	if realm:
		wwwA=wwwA+f' realm={realm}'	

	if atype=='Basic':
		sc=basic_auth(auth_val,file,wwwA)
	elif atype=='Digest':
		sc=digest_auth(auth_val,file, wwwA, method)
	return sc	


def parse_aval(s):
	dic={}	
	for line in s:
			k,v=line.split('=')
			dic[k]=v.strip('\"')
	return dic

def check_protection(f_path, method, auth_val):
	sc=200
	while True:
		fprotect=os.path.join(f_path,Auth)
		protected=os.path.exists(fprotect)
		if protected:
			sc=401
			print(f"filefound at {f_path}")
			file=open(fprotect, 'r').read().splitlines()
			sc=check_atype(auth_val, file, method)
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
	sc=check_protection(f_path, method, auth_val)
	return sc

#content=sys.argv[1]

#print(check_protection(content))




#def authorised():



# if not authorised:
# 	sc=401
# else:
# 	sc=200
# return sc

