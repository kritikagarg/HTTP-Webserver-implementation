import sys
import os


def fgrep(file, wrd):
	val=[line for line in file if line.startswith(wrd)]			
	return val


def exe_cgi(content):
	stream = os.popen(content)
	return stream.read()

def cgi_handler(server_res, content):
	op = exe_cgi(content).splitlines()
	server_res=server_res.splitlines()
	l_op=fgrep(op, "Location:" )
	if l_op:
		server_res[0]="HTTP/1.1 302 Found"
		server_res.app


