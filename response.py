import os, os.path
import imp_func, res_functions, e_tag
import datetime
from time import mktime, ctime
from wsgiref.handlers import format_date_time

now = datetime.datetime.utcnow()
Date = str(format_date_time(mktime(now.timetuple())))

Server="kitkat.2.0"

main_dict=imp_func.main_dict
status_code_dic= main_dict['status_code']
ld={}


def res_object(res_headers, sc , encode=False):  
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n'
	res_headers='\r\n'.join(f"{k}: {v}" for k,v in res_headers.items())
	res += res_headers+ '\r\n'
	res +='\r\n'
	if encode:
		res=res.encode()
	return res


def response_handler(sc, req, orignal_msg, connection, loc=None):
	method=req[0][0]
	#ld["status_code"]=str(sc)
	first_sc=str(sc)[:1]
	content_length='0'
	payload=None
	res_headers={}                  
	if first_sc=='2':
		content,c_path = imp_func.get_content(req)
		payload, content_length = res_functions.content_attribute(method, content, orignal_msg)					
		content_type = res_functions.get_content_type(method,content)
		if method!='TRACE':
			last_modified = str(format_date_time(os.stat(content).st_mtime))
			etag = e_tag.gen_etag(content)
			res_headers={'Last-Modified':last_modified, 'Etag':etag}
		if method=="OPTIONS":
			res_headers["Allow"]="GET, HEAD, OPTIONS, TRACE"

		res_headers.update({'Content-Length':content_length, 'Content-Type':content_type})

	elif first_sc == '3' and sc!=304:
		res_headers={'Location':loc}

	res_headers.update({'Content-Length':content_length,'Connection':connection})
	res=res_object(res_headers, sc)
	#print(res)
	res=res.encode()
	ld["content_length"] = content_length
	if payload:
		res = res + payload
	return res




