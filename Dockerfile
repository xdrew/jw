FROM python:3.7-stretch

RUN apt-get update -y && apt-get install -y libav-tools

ENV APP_DIR=/app
ENV DATA_DIR=/data

RUN mkdir -p ${APP_DIR} ${DATA_DIR}

VOLUME ${DATA_DIR}

COPY jwdownload.py ${APP_DIR}

WORKDIR ${APP_DIR}

ENTRYPOINT ["python", "-u", "jwdownload.py"]