import imp_func

Server="kitkat.2.0"

main_dict=imp_func.main_dict
status_code_dic= main_dict['status_code']
#connection="close"
# def res_object(res_headers_list, sc , Date):  
# status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
# res = status + '\r\n'
# res += 'Date: ' + Date + '\r\n'
# res += 'Server: '+ Server + '\r\n'
# res_headers= "\r\n".join("%s: %s" % tup for tup in res_headers_list)
# res += res_headers
# res +='\r\n'

def success_response_body(method,sc, Date, last_modified, content_length, etag, content_type, connection): #last_modified,content_length
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n' 
	if method!='TRACE':
		res += 'Last-Modified: ' + last_modified + '\r\n'
		res += 'ETag: ' + etag + '\r\n'
	res += 'Content-Length: ' + content_length + '\r\n'
	res += 'Content-Type: ' + content_type + '\r\n'
	res += 'Connection: ' + connection + '\r\n'
	if method=='OPTIONS':
		res += "Allow: GET, HEAD, OPTIONS, TRACE" +'\r\n'
	res += '\r\n'
	return res

def redirect_response_body(method,sc, Date, loc, content_length, connection): #last_modified,content_length, content_type, 
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n' 
	if sc not in {304}:
		res += 'Location: ' + loc + '\r\n'
	#res += 'Content-Type: ' + content_type + '\r\n'
	res += 'Content-Length: ' + content_length + '\r\n'
	res += 'Connection: ' + connection + '\r\n'
	res += '\r\n'
	return res

def err_response_body(sc, Date, connection, content_length, encode=False): 
	status="HTTP/1.1 "+str(sc)+' '+status_code_dic[sc]
	res = status + '\r\n'
	res += 'Date: ' + Date + '\r\n'
	res += 'Server: '+ Server + '\r\n' 	
	res += 'Content-Length: ' + content_length + '\r\n'
	res += 'Connection: ' + connection + '\r\n'
	if sc==405:
		res += "Allow:" +'\r\n'
	res += '\r\n'	
	if encode:
		res=res.encode()
	return res