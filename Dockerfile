FROM python:3.6

LABEL maintainer="Kritika Garg <@kritikagarg7>"

ENV  PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app/

EXPOSE 80

RUN chmod a+x echoserver.py

ENTRYPOINT ["./echoserver.py"]
