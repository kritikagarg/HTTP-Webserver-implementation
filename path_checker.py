import os
import imp_func
import re

r_config=imp_func.load_yaml('redirect.yaml')
r_config={k: tuple(v) for k, v in r_config.items()}
#content=imp_func.get_content(req)

def check_config_for_path(content):
	for regx in r_config:
		new_path=re.subn(regx,r_config[regx][1],content)
		if new_path[1]!=0:
			print("Match")
			sc=r_config[regx][0]
			loc=new_path[0]
			return sc,loc	

def check_path_existence(content):
	exist=os.path.exists(os.path.expanduser(os.path.normpath(content)))
	if exist:
		sc,loc=check_if_directory(content)
	else: 
		sc=404
		print("invalid path:"+content)
		loc=None	
	return sc,loc

def check_if_directory(content):
	sc=200
	loc=None
	if os.path.isdir(content):                  
		print("It's a directory:"+content+"  "+content[:1])           #RENDER IMAGE.HTML
		if content[-1:] != '/':
			print("no back slash at end")
			sc=301
			loc=content+'/'
	return sc, loc

def path_check(req):
	o_p=check_config_for_path(req[0][1])
	if o_p:
		sc,loc=o_p
	else:
		content=imp_func.get_content(req)
		sc,loc=check_path_existence(content)
	return sc, loc