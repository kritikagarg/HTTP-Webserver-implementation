import sys
import os
import os.path 
from urllib.parse import urlparse, unquote_plus
from ruamel import yaml
import direc_list
import datetime


virtual_uri="/.well-known/access.log"

def load_yaml(config='check.yaml'):
	file=open(config,'r')
	main_dict= yaml.safe_load(file)
	return main_dict

def check_log_path(c_path,method):
	if c_path==virtual_uri and method=='GET':
		return True
	else:
		return False

def ext_path(uri):
	path=urlparse(uri).path
	path=unquote_plus(path)
	return path

def get_content(req):
	uri=req[0][1]
	method=req[0][0]
	c_path=ext_path(uri)
	c=check_log_path(c_path,method)
	if c==True:
		content=log_path
	else:	
		#content=os.path.join(os.path.abspath(os.path.dirname(docroot)), path) --------> not working?
		content=docroot+c_path

		if os.path.isdir(content) and content.endswith('/'):
			if os.path.exists(content+"index.html"):
				content=content+"index.html"
			else:
				direc_list.dir_list(content)	
				content=content+"tmpDL.html"
	return content,c_path

def connect(req):
	connection="keep-alive"
	for tup in req:
		if tup[0] == "connection" :
			connection=tup[1]
	return connection


def log_dump(ip,req, sc,ld, uid="-", uname="-", logfile=sys.stderr):
	rl=" ".join(req[0])
	logdate = datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
	print(f'{ip} {uid} {uname} [{logdate}] "{rl}" {sc} {ld["content_length"]}', file=logfile)	
	

main_dict=load_yaml()
docroot = main_dict['Root_DIR']
docroot = os.getenv("DOCROOT", docroot)

log_dir = main_dict['log_dir']
log_path= os.getenv("LOG_DIR", log_dir) + main_dict['log_file']