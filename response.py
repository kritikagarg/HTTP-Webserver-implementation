import os, os.path
import imp_func, res_functions, e_tag, partial_check, nego
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

def chunking(payload):
	payload=payload.decode()
	chunks=payload.split('\n')
	p=[]
	for i in zip(chunks[0::2], chunks[1::2]): 
		chunk="\r\n".join(i)
		len_chunk=hex(len(chunk))			
		p.append(f"{len_chunk}\r\n{chunk}\r\n")

	payload="\r\n".join(p)
	return(str.encode(payload))



def response_handler(sc, req, orignal_msg, connection, loc, ndic, content):
	method=req[0][0]
	#ld["status_code"]=str(sc)
	first_sc=str(sc)[:1]
	content_length='0'
	payload=None
	res_headers = {}
	dynamic=False 
	content1=content
	content_type='text/html'                 
	if first_sc == '2':
		content1 , c_path = imp_func.get_content(req)
		comp, extension, lang, charset = res_functions.find_ext(content)

		if method!='TRACE':
			last_modified = str(format_date_time(os.stat(content).st_mtime))
			etag = e_tag.gen_etag(content)
			res_headers={'Last-Modified':last_modified, 'Etag':etag}

		if method == "OPTIONS":
			res_headers["Allow"] = "GET, HEAD, OPTIONS, TRACE"

		if sc==200:
			payload, content_length = res_functions.content_attribute(method, content, orignal_msg)

		if sc==206:
			payload, content_length, content_range = partial_check.partial_content(method, content)
			res_headers.update({'Content-Range': content_range})

		if lang:
			res_headers.update({'Content-Language':lang})
		if comp:
			res_headers.update({'Content-Encoding':comp})

		content_type = res_functions.get_content_type(extension, charset)
		if method=="TRACE":
			content_type="message/http"

		res_headers.update({'Content-Length':content_length, 'Content-Type':content_type})
		#print(content)
		p_name=os.path.basename(content)
		if p_name=="tmpDL.html" and method!='TRACE':
			content_length='-'
			dynamic=True

	else:
		if sc !=304:
			dynamic = True
			#msg = "<html>\n<head>\n<title>#SC#</title>\n</head>\n<body>\n<h1>#SC#</h1>>\n<h2>#StatusMessage#</h2>\n</body>\n</html>\n"
			msg = open("templates/meta_list.html",'r').read()
			msg = msg.replace('#SC#', str(sc))
			msg = msg.replace('#SM#', status_code_dic[sc])
			if sc in {300,406}:
				msg = msg.replace('----', nego.big_d['mid'])

			payload = str.encode(msg)
			content_length=len(payload)

		if sc in {301,302}:
			res_headers.update({'Location':loc})
	if ndic:
		res_headers.update(ndic)

	res_headers.update({'Content-Length':content_length})

	if dynamic:
		res_headers.update({'Transfer-Encoding': 'chunked'})
		res_headers.pop('Content-Length')
		if method!='HEAD':
			payload=chunking(payload)

	elif method=='GET':
		res_headers.update({'Accept-Range': 'bytes'})




	res_headers.update({'Content-Type':content_type,'Connection':connection})
	res=res_object(res_headers, sc)
	#print(res)
	res=res.encode()
	ld["content_length"] = content_length
	if payload and method!='HEAD':
		res = res + payload
	return res

