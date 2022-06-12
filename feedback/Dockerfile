#FROM python:3.8.13-bullseye
FROM python:3.7.13-buster

ARG UID=1000

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    locales curl vim ca-certificates gcc wget unzip fontconfig \
    alsa-utils pulseaudio flac psmisc libatlas-base-dev libgfortran5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo en_US.UTF-8 UTF-8 > /etc/locale.gen && \
    mkdir -p /usr/share/locale/ && \
    touch /usr/share/locale/locale.alias && \
    ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && echo Asia/Tokyo > /etc/timezone && \
    locale-gen && \
    update-locale LANG=en_US.UTF-8 && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    wget https://moji.or.jp/wp-content/ipafont/IPAexfont/IPAexfont00301.zip && \
    unzip IPAexfont00301.zip && \
    mkdir -p /usr/share/fonts/ipa && \
    cp IPAexfont00301/*.ttf /usr/share/fonts/ipa && \
    fc-cache -fv

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

RUN useradd -m -u ${UID} app

COPY ./requirements.txt /requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install schedule pyyaml

COPY scripts /scripts
COPY entrypoint.sh /entrypoint.sh
WORKDIR /scripts

ENTRYPOINT ["/entrypoint.sh"]
