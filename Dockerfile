FROM python:3-alpine

RUN apk add --update sudo

WORKDIR /
ADD dbalert.py /
ADD setup.py /
RUN sudo python3 -m pip install /

RUN crontab -l | { cat; echo "* * * * * sudo python3 /dbalert.py --min-delay 30 > /proc/1/fd/1 2>/proc/1/fd/2"; } | crontab -
CMD ["crond", "-f"]
