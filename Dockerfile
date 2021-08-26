FROM python:3.8-alpine

RUN pip install flask pymongo flask-cors requests urllib3 python-dateutil mongo

COPY pos.py /opt/pos.py

EXPOSE 5000

ENTRYPOINT FLASK_APP=/opt/pos.py flask run --host=0.0.0.0
