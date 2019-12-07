#!/usr/bin/env python3
import socket
import sys
import parser,req_checker, imp_func, response
import threading 

HOST= '0.0.0.0'
PORT= 8080
if len(sys.argv) > 1:
	HOST = sys.argv[1]
if len(sys.argv) > 2:
	PORT = int(sys.argv[2])


def req_handler(parsed_dic,orignal_msg):
	req=parsed_dic["req"]
	#print(req)
	connection='close'
	allow,loc,ndic,content=None,None,None,None
	auth_dic={}
	if parsed_dic["bad_req"]:
		sc=400
	else:
		client_payload=None
		if parsed_dic["is_payload"]:
			client_payload=parsed_dic["client_payload"]
			#do something with client payload 
		sc, allow, auth_dic, loc, ndic, content= req_checker.check_request(req, client_payload)
		#print(loc)
		connection= imp_func.connect(req)
	res = response.response_handler(sc, req, orignal_msg, connection, allow, loc, ndic, content, auth_dic)

	# if sc ==200 and method in {'GET', 'POST'} and if ext=='cgi':
	# cgi_res=handle_cgi(res, content)

	return res, connection, sc 

def client_handler(conn,addr):
	while True:
		try:
			data = []
			timeout=imp_func.main_dict['timeout']
			conn.settimeout(timeout)
			buf = conn.recv(5000)
			if not buf:
				conn.close()
				break
			try:
				while buf:
					data.append(buf)
					conn.settimeout(0.01)   
					buf = conn.recv(5000)

			except socket.timeout as e:
					pass
			data = b"".join(data)

			while True:
				#parsed_dic=dict(req=req, bad_req=BAD_R, is_payload=payload, client_payload=client_payload, is_residue=is_residue, residue=residue)
				parsed_dic=parser.request_parser(data)
				req=parsed_dic["req"]
				res, connection, sc = req_handler(parsed_dic, data)
				print(req)
				print(res)
				conn.sendall(res)

				imp_func.log_dump(addr[0],req, sc, response.ld ,logfile=lfile)

				if parsed_dic["is_residue"]:
					data=parsed_dic["residue"]
				else:
					break

		except socket.timeout as e:
			connection='close'
			res=response.res_object({'Content-Length':'0','Connection':connection}, 408, encode=True)		
			conn.sendall(res)
		#except:
		#	pass

		if connection == 'close':
			conn.close() 
			break


if __name__ == "__main__":	
	try:
		s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((HOST,PORT))
		s.listen()
		print("Listening on " + HOST + ":" + str(PORT))

		docroot = imp_func.docroot
		log_path = imp_func.log_path
		lfile=open(log_path,'a', buffering=1)
		while True:
			conn, addr = s.accept()
			print('accepted', conn, 'from', addr)
			client_thread=threading.Thread(target=client_handler, args= (conn, addr,))
			client_thread.start()
			print(threading.enumerate())

	except KeyboardInterrupt:
		s.close()
		print("Server Socket Closed")
		sys.exit()