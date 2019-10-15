#!/usr/bin/env python3
import socket
import sys
import os
import datetime
from time import mktime
from wsgiref.handlers import format_date_time
import imp_func, parser, req_checker, res_functions, res_body, conditional, e_tag

now = datetime.datetime.utcnow()
Date = str(format_date_time(mktime(now.timetuple())))

HOST= '0.0.0.0'
PORT= 8080
if len(sys.argv) > 1:
	HOST = sys.argv[1]
if len(sys.argv) > 2:
	PORT = int(sys.argv[2])

#________________Logs______________________
ld={}
def log_dump(ip,req,ld, uid="-", uname="-", logfile=sys.stderr):
	rl=" ".join(req[0])
	logdate = now.strftime("%d/%b/%Y:%H:%M:%S +0000")
	print(f'{ip} {uid} {uname} [{logdate}] "{rl}" {ld["status_code"]} {ld["content_length"]}', file=lfile)	
	
#____________________________________RESPONSE____________________________________
##CREATE res_headers_list : list of tuples

def response_handler(sc, req, orignal_msg, loc=None):
	connection= imp_func.connect(req)
	method=req[0][0]
	ld["status_code"]=str(sc)
	first_sc=str(sc)[:1]
	content_length='0'
	payload=None                  

	if first_sc in {'4','5'}:
		res=res_body.err_response_body(sc, Date, content_length, connection)
	elif first_sc=='2':
		content = imp_func.get_content(req)
		payload, content_length = res_functions.content_attribute(method, content, orignal_msg)					
		content_type = res_functions.get_content_type(method,content)
		last_modified = str(format_date_time(os.stat(content).st_mtime))
		etag = e_tag.gen_etag(content)
		res = res_body.success_response_body(method,sc, Date, last_modified, content_length, etag, content_type, connection) #last_modified,#content_length

	elif first_sc == '3':
		res=res_body.redirect_response_body(method,sc, Date, loc, content_length, connection)

	res=res.encode()
	ld["content_length"] = content_length
	if payload:
		res = res + payload
	return res


def req_handler(orignal_msg):
	req, sc, loc= req_checker.check_request(parser.request_parser(data))
	res = response_handler(sc, req, orignal_msg, loc)
	return res, req 


if __name__ == "__main__":	
	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST,PORT))
	s.listen(4)
	print("Listening on " + HOST + ":" + str(PORT))

	docroot = imp_func.docroot
	log_path = imp_func.log_path
	lfile=open(log_path,'a', buffering=1)

	while True:
		conn, addr = s.accept()
		print('accepted', conn, 'from', addr)
		try:
			data = []
			timeout=imp_func.main_dict['timeout']
			conn.settimeout(timeout)
			buf = conn.recv(5000)
			while buf:
				data.append(buf)
				conn.settimeout(0.03)
				buf = conn.recv(4096)
		except socket.timeout as e:
			pass
		except:
			pass
		data = b"".join(data)
		ip=addr[0]
		res,req=req_handler(data)
		conn.sendall(res)
		#print(res)
		log_dump(ip,req,ld,logfile=lfile)
		conn.close()
		#try:
			#Thread(target=handle_client, args=(conn, ip, port)).start()     ###check for IP
		#except:
		#	print("Error creating new thread for conn", ip, ":", port)
			
	s.close()
