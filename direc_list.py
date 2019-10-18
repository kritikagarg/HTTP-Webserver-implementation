import os
import os.path
import jinja2
from datetime import datetime


def get_path(c_path):
    if c_path.endswith('/'):
        c_path = c_path[:-1]
    return(c_path)

def get_time(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d  %H:%M")

def get_display_info(c_path):
    dis=dict(parent=c_path, p_name=os.path.basename(c_path), folder=[])
    with os.scandir(c_path) as it:
        for item in it:
            fname=item.name
            if item.is_file():
                icon="icons/file.gif"
                alt="[]"
                #link=os.path.join(c_path,fname)

            if item.is_dir():
                icon="icons/folder.gif"
                alt="[DIR]"
                #new_path=os.path.join(c_path,fname)
                #link=dir_list(new_path)
            print(c_path)
            print(fname)
            link=os.path.join(c_path,fname)
            print(link)
            info = item.stat()
            item_info = dict(name=fname, size=info.st_size, time=get_time(info.st_mtime), link=link, icon=icon, alt=alt)
            dis["folder"].append(item_info)
    return dis


# def dir_list(c_path):
#     return template.render(get_display_info(get_path(c_path)))

env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath='templates/'))

template = env.get_template('index_temp.html')

#c_path ='a2-test/'
#p_name=os.path.basename(get_path(c_path))
def dir_list(c_path):
    print(c_path)
    output=template.render(get_display_info(get_path(c_path)))
    #return(output)
    f=open(c_path+"index.html", 'w')
    f.write(output)


#output=dir_list(c_path)
#print(output)
#f=open("templates/"+p_name+".html", 'w')
#f.write(output)
