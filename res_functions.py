import imp_func
import fs

main_dict=imp_func.load_yaml()	
method_dict=main_dict['methods']  #method properties
char_dic=main_dict["charset_encoding"]
lang_dic=main_dict["language_encoding"]	
cmp_dic=main_dict["compression"]

#response-functions#______________________
def get_content_type(extension, charset):
	mime_support= main_dict['MimeTypes']     #main_dic
	try:	
		content_type=mime_support[extension]
	except:
		content_type="application/octet-stream"   #Default 
	if charset:
		content_type=f'{content_type}; charset={charset}'
	return content_type

def content_attribute(method, content, orignal_msg):
	payload=None
	content_length=0
	prop_dict=method_dict[method]
	if prop_dict['echo']: #TRACE
		payload=orignal_msg
		content_length=len(payload)
	else:
		if prop_dict['payload']:
			payload=fs.read(content)
		if prop_dict['content_length']:
			content_length=fs.size(content)	
	return payload , str(content_length)


def find_ext(content):	
	extension=content.split('.')[-1]
	charset=None
	lang,comp=None,None
	if extension in cmp_dic:
		comp=cmp_dic[extension]
		content=content.removesuffix('.'+extension)
		extension=content.split('.')[-1]

	if extension in char_dic:
		charset=char_dic[extension]
		content=content.removesuffix('.'+extension)
		extension=content.split('.')[-1]
	if extension in lang_dic:
		lang=extension
		content=content.removesuffix('.'+lang)
		extension=content.split('.')[-1]
	return comp, extension, lang, charset


