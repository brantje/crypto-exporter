#Deriving the latest base image
FROM python:latest

#Labels as key value pair
LABEL Maintainer="brantje"

WORKDIR /usr/app/src

COPY requirements.txt ./
RUN pip install -r requirements.txt

HEALTHCHECK CMD curl --fail http://localhost:8000 || exit 1   

COPY main.py ./
CMD [ "python", "./main.py"]
