import os
import os.path
from os import path
import imp_func
import direc_list

main_dict=imp_func.load_yaml()	
method_dict=main_dict['methods']  #method properties


def content_attribute(method, content, orignal_msg):
	payload=None
	content_length=0
	prop_dict=method_dict[method]
	if prop_dict['payload']:
		if prop_dict['echo']:
			#print("Hey!...its TRACE")
			payload=orignal_msg
			content_length=len(payload)

		else:
			payload=open(content, "rb").read()
			content_length=os.path.getsize(content)	
	return payload , str(content_length)


def find_ext(content):
	if './' in content:
		extension = content.split('.')[2]
#	if os.path.isdir(content):
#		extension="/"
	else:
		extension = content.split('.')[-1]
	return extension


def get_content_type(method,content):
	mime_support= main_dict['MimeTypes']     #main_dic
	extension=find_ext(content)
		           #can we get anhtml file of listing and change content to that html?
	if method=="TRACE":
		content_type="message/http"           ##CH
	else:
		try:	
			content_type=mime_support[extension]
		except:
			content_type="application/octet-stream"   #Default 
	return content_type





