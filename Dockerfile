# syntax=docker/dockerfile:1
FROM ubuntu:23.10
WORKDIR /home/root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 pip wget build-essential
COPY requirements.txt ./
RUN pip install -r requirements.txt --break-system-packages
ARG MT_VERSION=4.6.0 # Version of memtester to build and run
ENV MT_NAME memtester-${MT_VERSION}
ENV MT_ARCHIVE ${MT_NAME}.tar.gz
RUN wget https://pyropus.ca./software/memtester/old-versions/${MT_ARCHIVE} && \
    tar -xf ${MT_ARCHIVE} && cd ${MT_NAME} && make && mv memtester .. && \
    cd .. && rm -r ${MT_NAME} && rm ${MT_ARCHIVE}
COPY src/ ./
CMD python3 main.py --mt_args="100m 3" --mt_path=./memtester
