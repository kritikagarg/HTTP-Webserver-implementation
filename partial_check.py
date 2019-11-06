import re
import os.path as op
import imp_func
main_dict=imp_func.main_dict

rl={} #range_dictionary

def is_ascen(l):
	if sorted(l) == l:
		return True


def is_range(req):
	#print(req)
	is_range=False
	for tup in req:
		if tup[0]=="range":
			r_tup=tup[1]	                   
			try:
				unit,r_value = r_tup.split('=') 
				r_value = [i for i in re.split(", |(\d+)-" ,r_value)]        	#multiple ranges
				r_value = [int(i) for i in filter(None, r_value)]
				if 	is_ascen(r_value):#check if acsending order
					rl.update(dict(unit=unit,r_value=r_value))
					is_range = True
			except:
				pass 
	return is_range


def get_range(inp):
	r_value=inp
	n=len(r_value)
	if n==1:
		r_value.append(None)
	#if n==2:  #list of ranges 
	start, end = r_value
	return start, end

def check_partial(req):
	sc=200
	if is_range(req):
			sc=206
	return sc

def partial_payload(content):
	f=open(content, 'rb')
	start, end= get_range(rl["r_value"])
	if end:
		f.seek(start)
		diff=end-start+1
		payload=f.read(diff)
	else:
		if start < 0 :
			start=op.getsize(content)+start
		f.seek(start)
		payload=f.read()
		end=start+len(payload)-1
	rl.update(dict(start=start, end=end))	
	return payload

def partial_content(method, content):
	#print(rl)
	payload=None
	content_length=0
	payload = partial_payload(content)
	content_length = len(payload)
	size=op.getsize(content)
	content_range = f"{rl['unit']} {rl['start']}-{rl['end']}/{size}"
	if content_length==0:
		content_range=f"{rl['unit']} */{size}"
	return payload, content_length, content_range