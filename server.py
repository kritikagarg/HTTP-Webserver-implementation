#!/usr/bin/env python3
import socket
import sys
from ruamel import yaml
import re
import io
import datetime
import time
from time import mktime
from wsgiref.handlers import format_date_time
import os
from urllib.parse import urlparse
import req_checker

now = datetime.datetime.utcnow()
Date = str(format_date_time(mktime(now.timetuple())))


HOST= '0.0.0.0'
PORT= 8080
Server="kitkat.0.1"

if len(sys.argv) > 1:
	HOST = sys.argv[1]
if len(sys.argv) > 2:
	PORT = int(sys.argv[2])

#________________Logs______________________
ld={}  #log_dic
#def log_dump(ld, uid="-", uname="-", logfile=sys.stderr):

def log_dump(ld, uid="-", uname="-", logfile=sys.stderr):
	logdate=now.strftime("%d/%b/%Y:%H:%M:%S GMT")
	print(f'{ld["ip"]} {uid} {uname} [{logdate}] "{ld["req_line"]}" {ld["status_code"]} {ld["content_length"]}', file=lfile)	
	

#____________________________________RESPONSE____________________________________
def OK_response_body(method,sc, Date, last_modified, content_length, content_type, connection): #last_modified,content_length
	status_code_dic= main_dict['status_code']
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n' 
	res += 'Last-Modified: ' + last_modified + '\r\n'
	res += 'Content-Length: ' + content_length + '\r\n'
	res += 'Content-Type: ' + content_type + '\r\n'
	res += 'Connection: ' + connection + '\r\n'
	if method=='OPTIONS':
		res += "Allow: GET OPTIONS HEAD TRACE" +'\r\n'
	res += '\r\n'
	return res

def err_response_body(sc, Date, content_length, connection): 
	status_code_dic= main_dict['status_code']
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n' 	
	res += 'Content-Length: ' + content_length + '\r\n'
	res += 'Connection: ' + connection + '\r\n'
	res += '\r\n'	
	return res

def response_handler(sc, req, orignal_msg):
	docroot= main_dict['Root_DIR']
	mime_support= main_dict['MimeTypes']
	#print(docroot)
	connection='close'
	method=req[0][0]
	ld["status_code"]=str(sc)
	if sc in main_dict['error_code']:
		content_length='0' 
		res=err_response_body(sc, Date, content_length, connection)
		payload=None

	else:
		content=req_checker.get_content(req)
		#print(content)
	
		extension=find_ext(content)
		payload=send_payload(method, content, orignal_msg)

		if method=="TRACE":
			content_type="message/http"           ##CH
		else:
			try:	
				content_type=mime_support[extension]
			except:
				content_type="application/octet-stream"   #Default 
			
		content_length= str(os.path.getsize(content))
		##LAST MODIFIED date format
		last_modified= str(format_date_time(os.path.getmtime(content)))
		res=OK_response_body(method, sc, Date, last_modified, content_length, content_type, connection) #last_modified,#content_length

	res=res.encode()
	ld["content_length"]=content_length
	if payload:
		res= res + payload
	return res


def send_payload(method, content, orignal_msg):
	method_dict=main_dict['methods']
	prop_dict=method_dict[method]
	if prop_dict['payload']:
		if prop_dict['echo']:
			#print("Hey!...its TRACE")
			payload=orignal_msg
			#print(payload)
		else:
			payload=open(content, "rb").read()				
	else:
		payload=None
	return payload

def find_ext(content):
	if './' in content:
		extension = content.split('.')[2]
	else:
		extension = content.split('.')[-1]
	return extension

def request_parser(data):
	f=io.BytesIO(data)
	req_line=f.readline().decode("utf8").rstrip()
	req=[req_line]
	ld["req_line"]=req_line
	for line in f:
		line=line.replace(b'\r',b'')
		line=line.decode("utf8").rstrip()
		if line!="":
			reqheader,value= line.split(': ',1)
			req.append((reqheader,value))
	return req


def req_handler(data):
	orignal_msg=data
	req,sc=req_checker.check_req_line(request_parser(data))
	res=response_handler(sc,req,orignal_msg)
	return res, req 

if __name__ == "__main__":
	main_dict=req_checker.load_yaml()	
	docroot = main_dict['Root_DIR']
	docroot = os.getenv("DOCROOT", docroot)

	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST,PORT))
	s.listen(2)
	print("Listening on " + HOST + ":" + str(PORT))

	log_dir = main_dict['log_dir']
	log_dir = os.getenv("LOG_DIR", log_dir)
	log_file = main_dict['log_file']
	lfile=open(log_dir+log_file,'a', buffering=bufsize)

	while True:
		conn, addr = s.accept()
		print('accepted', conn, 'from', addr)
		try:
			data = []
			conn.settimeout(3)
			buf = conn.recv(5000)
			while buf:
				data.append(buf)
				conn.settimeout(0.03)
				buf = conn.recv(4096)
		except socket.timeout as e:
			pass
		except Exception as e:
			pass
		data = b"".join(data)
		ld["ip"]=addr[0]
		res,req=req_handler(data)
		conn.sendall(res)
		log_dump(ld,logfile=lfile)
		conn.close()
		#try:
			#Thread(target=handle_client, args=(conn, ip, port)).start()     ###check for IP
		#except:
		#	print("Error creating new thread for conn", ip, ":", port)
			
	s.close()
