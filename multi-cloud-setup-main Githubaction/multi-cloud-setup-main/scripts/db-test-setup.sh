#!/bin/bash

docker run --name postgresdb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=myapp \
  -e POSTGRES_PASSWORD=qwert12345 \
  -p 5432:5432 \
  -d postgres:14.15-alpine3.21

docker run \
  --name mysql-db \
  -e MYSQL_ROOT_PASSWORD=my-secret-pw \
  -e MYSQL_DATABASE=my_database \
  -e MYSQL_USER=my_user \
  -e MYSQL_PASSWORD=my_user_password \
  -p 3306:3306 \
  -d mysql:8.0