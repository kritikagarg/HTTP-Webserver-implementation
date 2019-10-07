FROM python:3.7

LABEL maintainer="Kritika Garg <@kritikagarg7>"

ENV  PYTHONUNBUFFERED=1
ENV  DOCROOT=/var/www/cs531server
ENV  LOG_FILE=/var/logs/access.log

ADD  sample/* $DOCROOT/
ADD  access.log $DOCROOT/

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt

EXPOSE 80

RUN chmod a+x *.py 

CMD ["./server.py", "0.0.0.0", "80"]
