import os
import hashlib
from hashids import Hashids
import imp_func
hashids = Hashids()

def get_md5(content):
	return hashlib.md5(open(content,'rb').read()).hexdigest()  #IF content changes

def gen_stat_hash(content):
	info = os.stat(content)
	i1, i2 = info.st_ino, int(info.st_mtime) #if file moves or get modified
	return hashids.encode(i1,i2)
	 
def gen_etag(content):
	md = get_md5(content)
	st = gen_stat_hash(content)
	etag = f'"{md}-{st}"'
	#create a cache to save etag computation
	return etag
	
# content = imp_func.get_content(req)
# etag=gen_etag(content)


