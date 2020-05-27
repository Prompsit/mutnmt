from app import app, db
from app.utils import user_utils, utils, tasks
from app.utils.tokenizer import Tokenizer
from app.models import Engine, RunningEngines, User
from app.utils.translation.joeywrapper import JoeyWrapper
from lxml import etree
from nltk.tokenize import sent_tokenize

# from bs4 import BeautifulSoup, Doctype

import zipfile
import os
import re
import shutil
import glob
import subprocess

import sys

class TranslationUtils:
    # Checks if an engine is running
    def get_running_engine(self, id):
        try:
            return RunningEngines.query.filter_by(engine_id=id).first()
        except:
            return None

    def get_user_running_engine(self, user_id):
        try:
            return RunningEngines.query.filter_by(user_id=user_id).first()
        except:
            return None

    def text(self, user_id, engine_id, lines):
        task = tasks.translate_text.apply_async(args=[user_id, engine_id, lines])
        return task.id

    def get_inspect(self, user_id, line):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            tokenizer = Tokenizer(user_engine.engine)
            tokenizer.load()

            n_best = []
            if line.strip() != "":
                line_tok = tokenizer.tokenize(line)
                n_best = self.translators[user_engine.engine_id].translate(line_tok, 5)
            else:
                return None

            return {
                "source": user_engine.engine.source.code,
                "target": user_engine.engine.target.code,
                "preproc_input": line_tok,
                "preproc_output": n_best[0],
                "nbest": [tokenizer.detokenize(n) for n in n_best],
                "alignments": [],
                "postproc_output": tokenizer.detokenize(n_best[0])
            }
        else:
            return None
            
    def deattach(self, user_id):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            db.session.delete(user_engine)

        db.session.commit()

    def generate_tmx(self, user_id, engine_id, chain_engine_id, text):
        task = tasks.generate_tmx.apply_async(args=[user_id, engine_id, chain_engine_id, text])
        return task.id

    def translate_file(self, user_id, engine_id, user_file_path, as_tmx = False, tmx_mode = None):
        task = tasks.translate_file.apply_async(args=[user_id, engine_id, user_file_path, as_tmx, tmx_mode])
        return task.id