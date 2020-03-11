from app import app
from app.utils import user_utils
from app.utils.tokenizer import Tokenizer
from app.models import Engine
from toolwrapper import ToolWrapper
import xml.etree.ElementTree as ElementTree
from bs4 import BeautifulSoup, Doctype

import zipfile
import os
import re
import shutil
import glob

import sys

class TranslationUtils:
    def __init__(self):
        self.running_joey = {}
        self.format_mappings = {
            ".pptx": r'.*(slide(s*))$',
            ".docx": r'.*(document.xml)$',
            ".xlsx": r'.*sharedStrings\.xml$',
            ".libreoffice": r'.*content\.xml$'
        }

    def launch(self, user_id, id):
        if user_utils.get_uid() in self.running_joey.keys():
            self.running_joey[user_utils.get_uid()]['slave'].close()

        engine = Engine.query.filter_by(id = id).first()
        slave = ToolWrapper(["python3", "-m", "joeynmt", "translate", os.path.join(engine.path, "config.yaml"), "-sm"],
                            cwd=app.config['JOEYNMT_FOLDER'])

        welcome = slave.readline()
        if welcome == "!:SLAVE_READY":
            self.running_joey[user_utils.get_uid()] = { "slave": slave, "engine": engine, "tokenizer": Tokenizer(engine) }
            return True

        return False

    def get(self, user_id, text): 
        if user_utils.get_uid() in self.running_joey.keys():
            user_context = self.running_joey[user_utils.get_uid()]
            if not user_context['tokenizer'].loaded:
                user_context['tokenizer'].load()

            joey = user_context['slave']
            joey.writeline(user_context['tokenizer'].tokenize(text))

            translation = joey.readline()
            return user_context['tokenizer'].detokenize(translation)
        else:
            return None

    def deattach(self, user_id):
        if user_utils.get_uid() in self.running_joey.keys():
            self.running_joey[user_utils.get_uid()]['slave'].close()
            del self.running_joey[user_utils.get_uid()]

    def norm_extension(self, extension):
        if extension in [".ppt", ".doc", ".xls"]:
            return extension + "x"
        elif extension in [".odp", ".odt", ".ods"]:
            return ".libreoffice"
        else:
            return extension

    def translate_office(self, user_id, file_path):
        filename, extension = os.path.splitext(file_path)
        norm_extension = self.norm_extension(extension)

        if norm_extension in self.format_mappings.keys():
            extract_path = '{}-extract'.format(filename)
            os.mkdir(extract_path)

            with zipfile.ZipFile(file_path, 'r') as zip:
                zip.extractall(extract_path)

            os.remove(file_path)

            for xml_file_path in [f for f in glob.glob(os.path.join(extract_path, "**/*.xml"), recursive=True)]:
                if re.search(self.format_mappings[norm_extension], xml_file_path):
                    self.translate_xml(user_id, xml_file_path)
            
            shutil.make_archive(filename, 'zip', extract_path, '.')
            shutil.move('{}.zip'.format(filename), file_path)
            shutil.rmtree(extract_path)

    def translate_txt(self, user_id, file_path):
        translated_path = '{}.translated'.format(file_path)

        with open(file_path, 'r') as source:
            with open(translated_path, 'w+') as target:
                for line in source:
                    if line.strip():
                        print(self.get(user_id, line.strip()), file=target)
        
        os.remove(file_path)
        shutil.move(translated_path, file_path)

    def translate_xml(self, user_id, xml_path):
        with open(xml_path, "r") as xml_file:
            def eat(node):
                text = node.find(text=True, recursive=False)
                if text and text.strip() and not isinstance(text, Doctype):
                    node.find(text=True, recursive=False).replace_with(self.get(user_id, text.string.upper()))

                for child in node.findChildren(recursive=False):
                    eat(child)

            soup = BeautifulSoup(xml_file, 'lxml')
            eat(soup)
            
        os.remove(xml_path)

        with open(xml_path, "w+") as xml_file:
            xml_file.write(soup.prettify())

    def translate_file(self, user_id, file_path):
        filename, extension = os.path.splitext(file_path)

        if extension in [".xml", ".html"]:
            self.translate_xml(user_id, file_path)
        elif extension == ".txt":
            self.translate_txt(user_id, file_path)
        else:
            self.translate_office(user_id, file_path)
        