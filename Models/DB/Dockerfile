# syntax=docker/dockerfile:1

#using the latest image from mariadb.
FROM mariadb:latest

# workdir. Can place scripts to run in here.
#WORKDIR /app

#insert sql file which is inserted into db upon container creation.
COPY ./dumps /home/dumps

