import os, imp_func


def create_file(content, client_payload):
	f=open(content,'wb')
	f.write(client_payload)
	print("Created")
	f.close()


def put(content, client_payload):
	exist=os.path.isfile(os.path.expanduser(os.path.normpath(content)))
	create_file(content, client_payload)	
	if exist:
		sc=200
	else:
		sc=201
	return sc


def delete(content):
	exist=os.path.isfile(os.path.expanduser(os.path.normpath(content)))
	if exist:
		os.remove(content)
		sc=200
		#payload="<html>\r\n<body>\r\n<h1>File deleted.</h1>\r\n</body>\r\n</html>"
	else:
		sc=405
	return sc


def unsafe_method_handler(req, client_payload):
 	method=req[0][0]
 	content,c_path=imp_func.get_content(req)
 	if method == "DELETE":
 		sc=delete(content)
 	if method == "PUT":
 		sc=put(content, client_payload)
 	return sc