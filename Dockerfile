FROM nvidia/cuda:10.2-base

RUN echo "Europe/Madrid" > /etc/timezone
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update -q --fix-missing && \
    apt-get -y upgrade && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
			python3 \
                        python3-dev \
                        autossh \
                        gcc \
                        redis \
                        virtualenv \
                        curl \
                        libreoffice \
                        libxml2-utils \
                        tzdata \
                        cmake \
                        git \
                        build-essential \
                        pkg-config \
                        libgoogle-perftools-dev && \
    apt-get autoremove -y && \
    apt-get autoclean

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
        apt-get install -y nodejs && curl -L https://npmjs.org/install.sh | sh

RUN mkdir /opt/mutnmt

COPY . /opt/mutnmt/

RUN /opt/mutnmt/scripts/install.sh

RUN /opt/mutnmt/scripts/minify.sh

CMD ./opt/mutnmt/scripts/docker-entrypoint.sh
