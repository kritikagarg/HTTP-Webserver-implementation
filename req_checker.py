import sys
from ruamel import yaml
import re
import io
import os
import os.path
import imp_func
import path_checker, conditional, partial_check, authorize, unsafe

main_dict=imp_func.load_yaml()

def check_headers(req):
	sc=200
	host_count=0
	h_list=[]                   
	for i in range(1,len(req)):
		header=req[i][0]         # To take all cases of headers ..host,HOST
		if header not in main_dict['reqheaders']:  #check for header supported, ex="      host  "  
			sc=400
			print("invalid header: "+(header))	
		if header=="host":   
			h_list.append(req[i])
			#print(host_count)	
	if len(h_list)!=1:
		sc=400		
		print("more than 1 host present OR no host")
	else:
		host_field=h_list[0][1]             #check for the valid host field
		valid=re.match("^[\w\.\-:]*$",host_field)
		if not valid:
			sc=400
			print("invalid host field")
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

def check_method(req):
	#print(req)
	m=req[0][0]
	check1= m.isalpha() and req[0][0].isupper()
	if check1:
		if m in main_dict['methods']:
#			sc=check_valid_path(req) 
			sc=check_version(req)
		else: 
			sc=501
			print("invalid method")	
	else:
		sc=400
		print("Method not good")	
	return sc


def check_request(req, client_payload):
	content,c_path = imp_func.get_content(req)
	sc=check_method(req)
	method=req[0][0]
	loc = None
	ndic,auth_dic =None,{}
	allow=[]
	auth_val=imp_func.get_reqheader_value("authorization", req)
	if len(auth_val) > 1:
		sc=400
	elif sc==200:
		sc, allow, auth_dic=authorize.check_authorised(content, method, client_payload, auth_val)
		#print(sc)
		if sc == 200:
			if method in {'DELETE','PUT'}:
				sc = unsafe.unsafe_method_handler(req, client_payload)
			else:
				sc, loc, ndic, content = path_checker.path_check(req)
				if sc == 200 and method in {'GET', 'HEAD'}:
					sc = conditional.check_conditional_requests(req, content) 
					if sc == 200:
						sc = partial_check.check_partial(req)
	return sc, allow, auth_dic, loc, ndic , content