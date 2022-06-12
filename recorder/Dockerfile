FROM python:3.8.13-buster
RUN pip install evdev pika redis pandas==1.4.2 requests

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    locales ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo en_US.UTF-8 UTF-8 > /etc/locale.gen && \
    mkdir -p /usr/share/locale/ && \
    touch /usr/share/locale/locale.alias && \
    ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && echo Asia/Tokyo > /etc/timezone && \
    locale-gen && \
    update-locale LANG=en_US.UTF-8 && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

COPY entrypoint.sh /entrypoint.sh
COPY scripts /scripts
ENTRYPOINT ["/entrypoint.sh"]
