FROM python:latest

RUN mkdir /opt/mutnmt

COPY scripts /opt/mutnmt/scripts

RUN echo "Europe/Madrid" > /etc/timezone

RUN apt-get update -q --fix-missing && \
    apt-get -y upgrade && \
    apt-get -y install virtualenv curl && \
    apt-get autoremove -y && \
    apt-get autoclean

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
        apt-get install -y nodejs && curl -L https://npmjs.org/install.sh | sh

RUN /opt/mutnmt/scripts/install.sh

RUN /opt/mutnmt/scripts/minify.sh

CMD ./opt/mutnmt/scripts/docker-entrypoint.sh