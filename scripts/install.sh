#!/bin/bash

cd /opt/mutnmt

npm install npm@latest -g
npm install postcss-cli autoprefixer sass -g

virtualenv -p /usr/bin/python3 venv

source venv/bin/activate
pip3 install -r scripts/requirements.txt

python3 -c 'import nltk; nltk.download("punkt")'

cd app/joeynmt
pip3 install .