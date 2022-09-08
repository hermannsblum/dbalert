FROM python:3-alpine

RUN apk add --update sudo tzdata

ENV TZ Europe/Berlin

WORKDIR /
ADD dbalert.py /
ADD setup.py /
RUN sudo python3 -m pip install /

ADD start.sh /
RUN chmod 775 /start.sh

CMD "/start.sh"
