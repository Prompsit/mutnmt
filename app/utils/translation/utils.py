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
    def set_admin(self, is_admin):
        self.is_admin = is_admin

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
        task = tasks.translate_text.apply_async(args=[user_id, engine_id, lines, self.is_admin])
        return task.id

    def get_inspect(self, user_id, engine_id, line, engines):
        task = tasks.inspect_details.apply_async(args=[user_id, engine_id, line, engines, self.is_admin])
        return task.id

    def get_compare(self, user_id, line, engines):
        task = tasks.inspect_compare.apply_async(args=[user_id, line, engines, self.is_admin])
        return task.id

            
    def deattach(self, user_id):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            db.session.delete(user_engine)

        db.session.commit()

    def generate_tmx(self, user_id, engine_id, chain_engine_id, text):
        task = tasks.generate_tmx.apply_async(args=[user_id, engine_id, chain_engine_id, text, self.is_admin])
        return task.id

    def translate_file(self, user_id, engine_id, user_file_path, as_tmx = False, tmx_mode = None):
        task = tasks.translate_file.apply_async(args=[user_id, engine_id, user_file_path, as_tmx, tmx_mode, self.is_admin])
        return task.id