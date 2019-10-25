import re 
import io
import sys
#data=open(sys.argv[1],"rb").read()

def request_parser(data):
	BAD_R=False
	# if data==b"":
	# 	BAD_R=True
	f=io.BytesIO(data)
	payload=False
	client_payload=b''

	req_line=f.readline().decode("utf8").rstrip()
	req=[req_line]
	req_line=req[0]
	req_line = re.match("^([A-Z]+)\s+(\S+)\s+([\w\/\.]+)$", req_line.replace("\r", ""))
	if req_line:	
		req[0]=(req_line[1],req_line[2],req_line[3])
	else:
		BAD_R=True
		print("invalid status line")

	for line in f:
		line=line.replace(b'\r',b'')
		line=line.decode("utf8").rstrip()
		try:
			reqheader,value= line.split(': ',1)
			reqheader=reqheader.lower()
			req.append((reqheader,value))
			if reqheader=="content-length":
				payload=True
				payload_size=int(value)
		except:
			if line=="":
				#print("End of headers")
				break
			else:
				BAD_R=True
				break

	if payload:
		client_payload=f.read(payload_size)

	is_residue=False
	residue=f.read()
	if residue not in {b'',b'\n'}:
		is_residue=True

	parsed_dic=dict(req=req, bad_req=BAD_R, is_payload=payload, client_payload=client_payload, is_residue=is_residue, residue=residue)
	return parsed_dic


#print(parsed_dic)

# if residue: #put some /
# 	print(f'residue is present')

# print(residue)
# print(req)
# print("content")
# print(client_payload)
# print(BAD_R)

#	
