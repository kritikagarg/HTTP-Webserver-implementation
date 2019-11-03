import sys, os , os.path, re
import hashlib, base64
import imp_func
#if 200 at end ... check authorisation

Auth=imp_func.main_dict['Auth']
docroot=imp_func.docroot
auth_dic={}


def check_dic(dic):
	val=''
	if 'authorization-type' in dic:
		val=dic['authorization-type']
	if 'realm' in dic:
		realm=dic['realm']
		val=val+f' realm={realm}'
	return(val)

def digest_auth(val,dic):
	sc=401
	auth_dic["WWW-Authenticate"]=f"Digest {val}"		
	return sc



def basic_auth(val, dic):
	sc=401
	usr,pswd=(base64.b64decode(val)).decode("utf-8").split(':')
	pswd=hashlib.md5(str.encode(pswd)).hexdigest()
	if usr in dic:
		if dic[usr]==pswd:
			sc=200
	return sc

def check_atype(auth_val, dic):
	sc=401
	if auth_val:
		atype,val=auth_val.strip().split(' ',1)
		if atype=='Basic':
			sc=basic_auth(val,dic)
		elif atype=='Digest':
			sc=digest_auth(val, dic)
	return sc	


def parse_fprotect(fprotect):
	dic={}
	file=open(fprotect, 'r').read().splitlines()
	for line in file:
		try:
			k,v=re.split(':|=',line)
			dic[k]=v
		except:
			continue
	return dic

def check_protection(f_path, auth_val):
	sc=200
	while True:
		fprotect=os.path.join(f_path,Auth)
		protected=os.path.exists(fprotect)
		if protected:
			sc=401
			print(f"filefound at {f_path}")
			dic=parse_fprotect(fprotect)
			auth_dic["WWW-Authenticate"]=check_dic(dic)		
			sc=check_atype(auth_val, dic)
			break
		else:
			if not os.path.samefile(f_path, docroot):
				f_path=os.path.join(f_path,'../')
			else:
				break
	return sc

def check_authorised(content, auth_val=None):
	f_name=os.path.basename(content)
	f_path=content.strip(f_name)	
	sc=check_protection(f_path, auth_val)
	return sc

#content=sys.argv[1]

#print(check_protection(content))




#def authorised():



# if not authorised:
# 	sc=401
# else:
# 	sc=200
# return sc

