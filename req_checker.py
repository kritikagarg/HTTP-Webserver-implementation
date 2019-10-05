import socket
import sys
import yaml
import re
import io
from urllib.parse import urlparse
import os
import os.path 


def load_yaml():
	file=open('check.yaml','r')
	main_dict= yaml.safe_load(file)
	return main_dict

#CHECK IF Header have any trailing spaces or other discrepancies    
##send 200 code at last
def check_headers(req):
	sc=200
	host_count=0                   
	for i in range(1,len(req)):
		header=req[i][0].lower()         # To take all cases of headers ..host,HOST
		if header not in main_dict['reqheaders']:  #check for header supported, ex="      host  "  
			sc=400
			print("invalid header")	
		if header=="host":   
			host_count+=1
			#print(host_count)	

	chost=req[1][0].lower()      #check if second line is Host or not		
	if chost!= "host":
		sc=400
		print("Second line is not host")
	else:
		host_field=req[1][1]             #check for the valid host field
		valid=re.match("^[\w\.\-:]*$",host_field)
		if not valid:
			sc=400
			print("invalid host field")
	if host_count>1:
		sc=400		
		print("more than 1 host present")
	return sc		


def check_version(req):
	ver=req[0][2]
	ver=ver.strip()
	if ver=="HTTP/1.1":
		sc=check_headers(req)
	else:
		sc=505
		print("invalid version")	
	return sc



def ext_path(uri):
	path = urlparse(uri).path
	return path

def get_content(req):
	uri=req[0][1]
	path=ext_path(uri)
	#print(path)
	#global content
	#content=os.path.join(os.path.abspath(os.path.dirname(docroot)), path) --------> not working?
	content=docroot+path
	return content


def check_valid_path(req):
	content=get_content(req)
	exist=os.path.exists(os.path.expanduser(os.path.normpath(content)))
	if open=='/home/kgarg/classwork/fall19/cs531/.well-known/access.log':
		sc=200

	if exist:
		sc=check_version(req)      
	else: 
		sc= 404
		print("invalid path:"+content)	
	return sc

def check_method(req):
	m=req[0][0]
	check1= m.isalpha() and req[0][0].isupper()
	if check1:
		if m in main_dict['methods']:
			# sc=check_valid_uri(req)
			sc=check_valid_path(req) 
		else: 
			sc=501
			print("invalid method")	
	else:
		sc=400
		print("Method not good")	
	return sc

def check_req_line(req):  #req_line=req[0]
	req_line=req[0]
	req_line = re.match("^([A-Z]+)\s+(\S+)\s+([\w\/\.]+)$", req_line.replace("\r", ""))
	if req_line:	
		req[0]=(req_line[1],req_line[2],req_line[3])
		sc=check_method(req)
	else:
		sc=400
		print("invalid status line")	
	return req, sc 

main_dict=load_yaml()
docroot= main_dict['Root_DIR']

#req=['GET http://127.0.0.1:8080/a1-test/2/index.html HTTP/1.1', ('host', '127.0.0.1:8080'), ('Connection', 'close')]

#req, sc=check_req_line(req)

#print('status_code:'+str(sc))
#print(req)
#print(get_content(req))

