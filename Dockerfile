FROM python:3.7

LABEL maintainer="Kritika Garg <@kritikagarg7>"

ENV  PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt

EXPOSE 80

RUN chmod a+x *.py 

CMD ["./server.py", "0.0.0.0", "80"]