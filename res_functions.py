import os
import os.path
from os import path
import imp_func
import direc_list

main_dict=imp_func.load_yaml()	
method_dict=main_dict['methods']  #method properties
char_dic=main_dict["charset_encoding"]
lang_dic=main_dict["language_encoding"]	
#response-functions#______________________
def get_content_type(method, extension, charset):
	mime_support= main_dict['MimeTypes']     #main_dic
		           #can we get anhtml file of listing and change content to that html?
	if method=="TRACE":
		content_type="message/http"           ##CH
	else:
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
			payload=open(content, "rb").read()
		if prop_dict['content_length']:
			content_length=os.path.getsize(content)	
	return payload , str(content_length)


def find_ext(content):	
	extension=content.split('.')[-1]
	charset=None
	lang=None
	if extension in char_dic:
		charset=char_dic[extension]
		content=content.strip('.'+extension)
		extension=content.split('.')[-1]
	if extension in lang_dic:
		lang=extension
		content=content.strip('.'+lang)
		extension=content.split('.')[-1]
	return extension, lang, charset








