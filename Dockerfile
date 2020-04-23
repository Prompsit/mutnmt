FROM nvidia/cuda:latest

RUN mkdir /opt/mutnmt

COPY scripts /opt/mutnmt/scripts

RUN echo "Europe/Madrid" > /etc/timezone

RUN apt-get update -q --fix-missing && \
    apt-get -y upgrade && \
    apt-get -y install  python3 \
                        python3-dev \
                        virtualenv \
                        curl &&
                        tzdata && \
    apt-get autoremove -y && \
    apt-get autoclean

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
        apt-get install -y nodejs && curl -L https://npmjs.org/install.sh | sh

RUN /opt/mutnmt/scripts/install.sh

RUN /opt/mutnmt/scripts/minify.sh

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

CMD ./opt/mutnmt/scripts/docker-entrypoint.sh