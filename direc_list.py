import os
import os.path
import jinja2
from datetime import datetime


def get_path(path):
    if path.endswith('/'):
        path = path[:-1]
    return(path)

def get_time(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d  %H:%M")

def get_display_info(path):
    dis=dict(parent=path, p_name=os.path.basename(path), folder=[])
    with os.scandir(path) as it:
        for item in it:
            fname=item.name
            if item.is_file():
                icon="icons/file.gif"
                alt="[]"
                #link=os.path.join(path,fname)

            if item.is_dir():
                icon="icons/folder.gif"
                alt="[DIR]"
                #new_path=os.path.join(path,fname)
                #link=dir_list(new_path)
            link=os.path.join(path,fname)
            info = item.stat()
            item_info = dict(name=fname, size=info.st_size, time=get_time(info.st_mtime), link=link, icon=icon, alt=alt)
            dis["folder"].append(item_info)
    return dis


# def dir_list(path):
#     return template.render(get_display_info(get_path(path)))

env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath='templates/'))

template = env.get_template('index_temp.html')

#path ='/home/kgarg/classwork/fall19/webserverDesign/A2/cs531/a2-test/'
#p_name=os.path.basename(get_path(path))
def dir_list(path):
    output=template.render(get_display_info(get_path(path)))
    f=open(path+"index.html", 'w')
    f.write(output)


#output=dir_list(path)

#f=open("templates/"+p_name+".html", 'w')
#f.write(output)
