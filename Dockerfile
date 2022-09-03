FROM python:3

ADD dbalert.py /
ADD setup.py /
RUN pip install .


