FROM python:3-alpine

RUN apk add --update sudo
#RUN apt update && apt install --yes sudo cron

WORKDIR /
ADD dbalert.py /
ADD setup.py /
RUN sudo python3 -m pip install /

ADD start.sh /
RUN chmod 775 /start.sh

RUN crontab -l | { cat; echo "* * * * * . /project_env.sh; python3 /dbalert.py > /proc/1/fd/1 2>/proc/1/fd/2"; } | crontab -
CMD "/start.sh"
