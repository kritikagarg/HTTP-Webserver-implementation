#!/usr/bin/env python3
import socket
import sys
import os
import datetime
from time import mktime, ctime
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
def log_dump(ip,req, sc,ld, uid="-", uname="-", logfile=sys.stderr):
	rl=" ".join(req[0])
	logdate = now.strftime("%d/%b/%Y:%H:%M:%S +0000")
	print(f'{ip} {uid} {uname} [{logdate}] "{rl}" {sc} {ld["content_length"]}', file=lfile)	
	
#____________________________________RESPONSE____________________________________
##CREATE res_headers_list : list of tuples

def response_handler(sc, req, orignal_msg, connection, loc=None):
	method=req[0][0]
	#ld["status_code"]=str(sc)
	first_sc=str(sc)[:1]
	content_length='0'
	payload=None                  

	if first_sc in {'4','5'}:
		res=res_body.err_response_body(sc, Date, connection, content_length)
	elif first_sc=='2':
		content,c_path = imp_func.get_content(req)
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


def req_handler(parsed_dic,orignal_msg):
	req=parsed_dic["req"]
	if parsed_dic["bad_req"]:
		sc=400
		connection='close'
		loc=None
	else:
		#if parsed_dic["is_payload"]:
			#parsed_dic["client_payload"]
			#do something with client payload 
		req, sc, loc= req_checker.check_request(req)
		connection= imp_func.connect(req)
	res = response_handler(sc, req, orignal_msg, connection, loc)
	return res, req, connection, sc 



if __name__ == "__main__":	
	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST,PORT))
	s.listen(3)
	print("Listening on " + HOST + ":" + str(PORT))

	docroot = imp_func.docroot
	log_path = imp_func.log_path
	lfile=open(log_path,'a', buffering=1)
	#timeout=imp_func.main_dict['timeout']
	while True:
		#print(f'Time1:{ctime()}') 
		conn, addr = s.accept()
		print('accepted', conn, 'from', addr)
		while True:
			try:
				data = []
				timeout=imp_func.main_dict['timeout']
				conn.settimeout(timeout)
				#print(f'Time2:{ctime()}') 
				buf = conn.recv(5000)
				if not buf:
					conn.close()
					break
				#print(f'Time3:{ctime()}')
				try:
					while buf:
						data.append(buf)
						#print(f'Time4:{ctime()}')
						conn.settimeout(0.01)   
						buf = conn.recv(5000)
						#print(b"buf:"+buf)
						#print(f'Time5:{ctime()}')
				except socket.timeout as e:
						pass
				#conn.settimeout(timeout) 
				data = b"".join(data)
				#print(b"Data:"+data)

				while True:
		#parsed_dic=dict(req=req, bad_req=BAD_R, is_payload=payload, client_payload=client_payload, is_residue=is_residue, residue=residue)
					parsed_dic=parser.request_parser(data)
					res, req, connection, sc = req_handler(parsed_dic, data)
					conn.sendall(res)

					log_dump(addr[0],req, sc, ld,logfile=lfile)

					if parsed_dic["is_residue"]:
						data=parsed_dic["residue"]
					else:
						break

			except socket.timeout as e:
				connection='close'
				#print(f'Time6:{ctime()}') 
				res=res_body.err_response_body(408, Date, connection, content_length='0', encode=True)
				conn.sendall(res)
			except:
				pass

			#print(res)
			if connection == 'close':
				conn.close() 
				break
				#print(f'Time8:{ctime()}')
			#try:
			#Thread(target=handle_client, args=(conn, ip, port)).start()     ###check for IP
		#except:
		#	print("Error creating new thread for conn", ip, ":", port)			
	s.close()