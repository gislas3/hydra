# pull official base image
FROM python:3.8.7-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents Python from writing pyc files to disc equivalent to python -B
ENV PYTHONUNBUFFERED 1  # Prevents Python from buffering stdout and stderr equivalent to python -u

# install dependencies
RUN pip install --upgrade pip --no-cache-dir
COPY ./requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# copy project
COPY . /usr/src/app

ARG RUN_ENVIRONMENT="dev"
ENV RUN_ENVIRONMENT=$RUN_ENVIRONMENT

RUN ["chmod","+x","/usr/src/app/hydra/third_party_scripts/run.sh"]
CMD ["/usr/src/app/hydra/third_party_scripts/run.sh"]