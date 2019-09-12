FROM python:3.6

LABEL maintainer="Kritika Garg <@kritikagarg7>"

WORKDIR /app

COPY /echoserver/ /app/

EXPOSE 80

RUN chmod a+x /echoserver/echoserver.py

ENTRYPOINT ["./echoserver/echoserver.py"]
#ENTRYPOINT ["./echoserver.py"]
