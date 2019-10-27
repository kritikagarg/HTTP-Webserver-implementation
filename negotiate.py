import os
import mimetypes

f_list=[]

#Request headers–Accept–Accept-Charset–Accept-Encoding–Accept-Language–Negotiate (from RFC 2295)
#Response headers–Content-Location–Vary–TCN (from RFC 2295)–Alternates (from RFC 2295)
def get_reqheader_value(header, req):
	value=None
	for tup in req:  ##need to feed in req
		if tup==header:
			value=tup[1]
	return value


#def read_accept(req):
#	a=get_reqheader_value(header, req)
#	if a:

def get_file_list(content):
	f_name=os.path.basename(content)
	f_path=content.strip(f_name)
	fl=[]
	#print(f'content:{content} f_name:{f_name} f_path:{f_path}')
	for item in os.scandir(f_path):
		fname=item.name
		if fname.startswith(f_name):		
			size=item.stat().st_size
			ftype= mimetypes.guess_type(fname)[0]
			f_list.append(f'<li><a href="{fname}">{fname}</a> , type {ftype}')
			fl.append(f'\u007b"{fname}" 1 \u007btype {ftype}\u007d \u007blength {size}\u007d\u007d')

	return(", ".join(fl))


def check_negotiation(content, req):
	ndic={}
	sc=404
	a=get_reqheader_value("accept", req)
	if not a: #check_acceptheader	
		print("No Accept header present")
		try:
			fl=get_file_list(content) #check multiple representations
			if fl:
				sc=300
				ndic.update({'Alternates':fl})
		except:
			sc=404
	#else:
		#check q value
	return ndic, sc


# mid1=" ".join(f_list)
# mid="<p>An appropriate representation of the requested resource could not be found on this server.</p><P>Available variants:<ul>mid1</ul>"
# mid= mid.replace('mid1', mid1)
# del f_list







