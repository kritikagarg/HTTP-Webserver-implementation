import io

def request_parser(data):
	f=io.BytesIO(data)
	req_line=f.readline().decode("utf8").rstrip()
	req=[req_line]
	for line in f:
		line=line.replace(b'\r',b'')
		line=line.decode("utf8").rstrip()
		if line!="":
			reqheader,value= line.split(': ',1)
			req.append((reqheader.lower(),value))
	return req