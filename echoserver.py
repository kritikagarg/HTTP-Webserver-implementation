#!/usr/bin/env python3
import socket

HOST= '0.0.0.0'
PORT= 80

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST,PORT))
	s.listen()
	print("Listening on " + HOST + ":" + str(PORT))
	s.setblocking(False)

	client_host,client_port = s.accept()
	with client_host:
		print('Connected by', client_port)
		while True:
			msg=client_host.recv(1024)   
			if not msg:
				break
			client_host.sendall(msg)


