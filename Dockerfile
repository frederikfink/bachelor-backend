# syntax=docker/dockerfile:1

# Use python 3.9
FROM python:3.9-slim-buster

#create workdir to keep files in.
WORKDIR /app

#copy requirements
COPY requirements.txt requirements.txt

#install requirements.
RUN pip3 install -r requirements.txt

#copy content of solution to container.
COPY . .

#run the solution
CMD ["python3", "main.py"]