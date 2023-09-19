#FROM python:3.10.7
#ENV PYTHONDONTWRITEBYTECODE=1
#ENV PYTHONUNBUFFERED=1
#RUN mkdir /newtech-web
#WORKDIR /newtech-web
#COPY ./src/requirements.txt /newtech-web/
#RUN pip install -r requirements.txt
#COPY ./src /newtech-web/

FROM php:7.4-fpm
RUN php -v
RUN apt-get update -y
RUN apt-get install libsodium-dev -y
RUN docker-php-ext-install sodium
RUN php -m

RUN apt-get install -y --no-install-recommends \
    python3 \
    python3-pip

RUN python3 --version
RUN pip --version

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN mkdir /vue-web
WORKDIR /vue-web
COPY ./back-end/src/requirements.txt /vue-web/
RUN pip install -r requirements.txt
COPY ./back-end/src /vue-web/
