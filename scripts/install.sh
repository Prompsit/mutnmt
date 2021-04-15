#!/bin/bash

cd /tmp
git clone https://github.com/google/sentencepiece.git
cd sentencepiece
mkdir build
cd build
cmake ..
make -j $(nproc)
make install
ldconfig -v

cd /opt/mutnmt

git submodule update --init --recursive

npm install npm@latest -g
npm install postcss-cli autoprefixer sass postcss -g

virtualenv -p /usr/bin/python3.8 venv

source venv/bin/activate
pip3 install -r scripts/requirements.txt

python3 -c 'import nltk; nltk.download("punkt")'

cd app/joeynmt
pip3 install .

[ -f "/opt/mutnmt/app/base/transformer.yaml" ] && rm /opt/mutnmt/app/base/transformer.yaml
ln -s /opt/mutnmt/app/base/transformer-small.yaml /opt/mutnmt/app/base/transformer.yaml
