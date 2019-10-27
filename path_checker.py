import os
import imp_func, nego
import re

r_config=imp_func.load_yaml('redirect.yaml')
r_config={k: tuple(v) for k, v in r_config.items()}

def check_config_for_path(content):
	for regx in r_config:
		new_path=re.subn(regx,r_config[regx][1],content)
		if new_path[1]!=0:
			sc=r_config[regx][0]
			loc=new_path[0]
			return sc,loc	

def check_path_existence(content,c_path, req):
	loc,ndic=None,None
	exist=os.path.exists(os.path.expanduser(os.path.normpath(content)))
	if exist:
		sc,loc=check_if_directory(content,c_path)
	else: 
		ndic, sc, content = nego.con_negotiate(content,req)
	return sc,loc,ndic, content


def check_if_directory(content,c_path):
	sc=200
	loc=None
	if os.path.isdir(content):                  
		print("It's a directory:"+content+"  "+content[:1])           #RENDER IMAGE.HTML
		if content[-1:] != '/':
			print("no back slash at end")
			sc=301
			loc=c_path+'/'
	return sc, loc

def path_check(req):
	content,c_path=imp_func.get_content(req)
	ndic=None
	o_p=check_config_for_path(req[0][1])
	if o_p:
		sc,loc=o_p
	else:
		sc,loc, ndic, content=check_path_existence(content,c_path,req)
	return sc, loc, ndic, content