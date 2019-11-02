import os
import mimetypes
import res_functions, imp_func

big_d={}

def get_fileList(f_name, f_path):
	fileList=[]
	try:
		for item in os.scandir(f_path):
			fname=item.name
			if fname.startswith(f_name):
				new_path=os.path.join(f_path,fname)
				comp, extension, lang, charset=res_functions.find_ext(new_path)
#				ftype= mimetypes.guess_type(fname)[0]
				ftype=res_functions.get_content_type(extension, charset)
				size=item.stat().st_size
				s=(ftype,fname,size)
				if lang:
					s=(lang,fname,size)
				fileList.append(s)				
	except:
		fileList=[]
	return fileList


def get_fs(inp):
	al=[]
	ml=[]
	for f in inp:
		ftype,fname,size=f
		al.append(f'\u007b"{fname}" 1 \u007btype {ftype}\u007d \u007blength {size}\u007d\u007d')
		ml.append(f'<li><a href="{fname}">{fname}</a> , type {ftype}')
	fs=(", ".join(al))
	mid=('\n'.join(ml))
	return fs, mid


def tie(sa):
	ct=[t[0] for t in sa]
	if len(set(ct))==1:
		return True 

def read_accept(a):
	sa=[]
	a=a.split(', ')
	for i in a:
		v,k=i.split('; ')
		sa.append((float(k.strip('q=')),v))
	sa=sorted(sa, reverse=True)
	print(sa)
	return sa


#Vary: "All the Accept related headers"
def con_negotiate(content,req):
	f_name=os.path.basename(content)
	f_path=content.strip(f_name)
	ndic={}
	fileList=get_fileList(f_name, f_path)
	print(fileList)
	if fileList:
		sc=300
		fs, mid=get_fs(fileList)
		big_d["mid"]=get_mid(mid)
		val=imp_func.get_reqheader_value("accept", req)
		if not val:
			ndic.update({'Alternates':fs})
		if val:
			vary=f'negotiate, {", ".join([t[0] for t in val])}'
			for tup in val:
				a=tup[1]
				sa=read_accept(a)
				if tie(sa):
					print('TIE')
					sc=300
					ndic.update({'Alternates':fs})
					break

				else:	
					m=[]
					for atyp in sa:
						atype=atyp[1]
						if '*' in atype:
							atype=atype.strip('*')

						m=[u for u in fileList if atype in u[0]]
						print(atype)
						print(m)
						if m:
							if len(m)==1:
								sc=200
								content=os.path.join(f_path,m[0][1])
								ndic.update({'Vary': vary })
							if len(m)> 1:
								sc=300
								ndic.update({'Alternates':fs})
							break
						else:
							continue

					if m==[]:
						sc=406
						ndic.update({'Alternates':fs, 'Vary': vary})											
	else:
		sc=404
	return ndic, sc, content


def get_mid(mid1):
	mid="<p>An appropriate representation of the requested resource could not be found on this server.</p>\n<P>Available variants:\n<ul>\nmid1\n</ul>"
	mid= mid.replace('mid1', mid1)
	return mid
			