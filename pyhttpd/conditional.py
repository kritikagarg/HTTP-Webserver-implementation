from datetime import datetime
from wsgiref.handlers import format_date_time
from dateutil.parser import parse
import os
from . import e_tag, imp_func, fs


def valid_date(date_text):
	try:
		datetime.strptime(date_text, "%a, %d %b %Y %H:%M:%S GMT")
		c=True
	except:
		c=False
	return c	

def check_modified(method, if_dict, last_modified):
	if method in {'GET','HEAD'}:
		sc=200
		c_date=if_dict["if-modified-since"]
		if valid_date(c_date):
			s_Date=parse(last_modified)
			c_date=parse(c_date)
			if s_Date > c_date:
				sc=200
			else:
				sc=304
	return sc
			
def check_unmodified(if_dict, last_modified, etag, method):
	sc=200
	c_date=if_dict["if-unmodified-since"]
	if valid_date(c_date):
		s_Date=parse(last_modified)
		c_date=parse(c_date)
		if s_Date > c_date:
			sc=412

	if sc==200:
		if "if-none-match" in if_dict:
			sc=check_none_match(if_dict, etag, method)	
	return sc

def check_match(if_dict, etag, method):
	c_tags=if_dict["if-match"].split(',')
	for tag in c_tags:
		tag=tag.strip()
		if etag==tag:
			sc=200
			if "if-none-match" in if_dict:
				sc=check_none_match(if_dict, etag, method)
			break
		else:
			sc=412
	return sc

def check_none_match(if_dict, etag, method):
	sc=200
	c_tags=if_dict["if-none-match"].split(',')
	for tag in c_tags:
		tag=tag.strip()
		if etag==tag:
			if method in {'GET','HEAD'}:
				sc=304
			else:
				sc=412
			break
	return sc


def get_if_dict(req):
	#print(req)
	if_dict={}
	for tup in req:
		if tup[0].startswith("if"):
			if_dict[tup[0]]=tup[1]
	return if_dict


def check_conditional_requests(req, content):
	method=req[0][0]
	last_modified = str(format_date_time(fs.mtime(content)))
	etag = e_tag.gen_etag(content)
	if_dict=get_if_dict(req)
	sc=200

	if "if-match" in if_dict:
		sc=check_match(if_dict, etag, method)
	
	elif "if-unmodified-since" in if_dict:
		sc=check_unmodified(if_dict, last_modified, etag, method)

	# RFC 9110 13.2.2: If-None-Match is evaluated on its own, and
	# If-Modified-Since only when no If-None-Match is present.
	elif "if-none-match" in if_dict:
		sc=check_none_match(if_dict, etag, method)

	elif "if-modified-since" in if_dict:
		sc=check_modified(method,if_dict,last_modified)

	return sc


			


