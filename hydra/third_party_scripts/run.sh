#!/bin/bash

# Migrate existing migrations
# Note: DO NOT create the migrations at this step
#       The migrations should be committed and pushed beforehand

HOST=0.0.0.0:8000

python manage.py migrate
if [ "$RUN_ENVIRONMENT" == "production" ]
then
  # Run Prod
  echo "Running with Gunicorn"
  python manage.py collectstatic \
  && gunicorn hydra.wsgi -b $HOST
else
  # Run Dev
  python manage.py runserver $HOST
fi