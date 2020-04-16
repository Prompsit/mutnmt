from app import app, db
from app.utils import user_utils
from app.utils.tokenizer import Tokenizer
from app.models import Engine, RunningEngines, User
from app.utils.translation.joeywrapper import JoeyWrapper
from lxml import etree
from nltk.tokenize import sent_tokenize
from sqlalchemy import inspect as sa_inspect
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
    def __init__(self):
        # { engine: JoeyWrapper }
        self.translators = {}

        self.format_mappings = {
            ".pptx": r'.*(slide(s*))$',
            ".docx": r'.*(document.xml)$',
            ".xlsx": r'.*sharedStrings\.xml$',
            ".libreoffice": r'.*content\.xml$'
        }
        
        self.format_filters = {
            ".pdf": "odg",
            ".rtf": "docx"
        }

        self.sentences = {}

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


    def launch(self, user_id, id):
        user = User.query.filter_by(id=user_id).first()
        engine = Engine.query.filter_by(id=id).first()

        # If the engine is currently running, we add the user to it
        # If the user is already added, we do nothing
        # If the user is running another engine, we switch
        # If the user is not running anything, we add them to the engine
        engine_entry = self.get_running_engine(id)
        user_engine = self.get_user_running_engine(user_id)

        print([engine_entry, user_engine], file=sys.stderr)
        
        if engine_entry:
            if user_engine and engine_entry.engine.id == user_engine.engine.id:
                return True
        else:
            self.translators[engine.id] = JoeyWrapper(engine.path)
            self.translators[engine.id].load()

        # If this user is already using another engine, we switch
        if user_engine: db.session.delete(user_engine)
        user.user_running_engines.append(RunningEngines(engine=engine, user=user))

        db.session.commit()

        return True

    def get(self, user_id, lines):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            tokenizer = Tokenizer(user_engine.engine)
            tokenizer.load()

            translations = []
            for line in lines:
                if line.strip() != "":
                    line_tok = tokenizer.tokenize(line)
                    translation = self.translators[user_engine.engine_id].translate(line_tok)
                    translations.append(tokenizer.detokenize(translation))
                else:
                    translations.append("")

            return translations
        else:
            return None

    def get_line(self, user_id, line):
        translation = self.get(user_id, [line])
        return translation[0] if translation else None

    def get_inspect(self, user_id, lines):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            return [self.translators[user_engine.engine_id].translate(line) for line in lines]
        else:
            return None

    def deattach(self, user_id):
        user_engine = self.get_user_running_engine(user_id)
        if user_engine:
            db.session.delete(user_engine)

            # We check again, if nothing is found, no user is translating with that engine
            if not self.get_running_engine(user_engine.engine_id):
                del self.translators[user_engine.engine_id]

        db.session.commit()

    def norm_extension(self, extension):
        if extension in [".ppt", ".doc", ".xls"]:
            return extension + "x"
        elif extension in [".odp", ".odt", ".ods", ".odg"]:
            return ".libreoffice"
        else:
            return extension

    def translate_txt(self, user_id, file_path, as_tmx = False):
        translated_path = '{}.translated'.format(file_path)
        with open(file_path, 'r') as source:
            with open(translated_path, 'w+') as target:
                for line in source:
                    translation = self.get_line(user_id, line)
                    if as_tmx: self.sentences[str(user_id)].append({ "source": line.strip(), "target": [translation] })
                    print(translation, file=target)
    
        os.remove(file_path)
        shutil.move(translated_path, file_path)

    def translate_xml(self, user_id, xml_path, mode = "xml", as_tmx = False):
        def explore_node(node):
            if node.text and node.text.strip():
                translation = self.get_line(user_id, node.text)
                if as_tmx: self.sentences[str(user_id)].append({ "source": node.text, "target": [translation] })
                node.text = translation
            for child in node:
                explore_node(child)
        
        with open(xml_path, 'r') as xml_file:
            parser = etree.HTMLParser() if mode == "html" else etree.XMLParser()
            tree = etree.parse(xml_file, parser)
            explore_node(tree.getroot())

        tree.write(xml_path, encoding="UTF-8", xml_declaration=(mode == "xml"))

    def translate_tmx(self, user_id, tmx_path, tmx_mode):
        sentences = []

        with open(tmx_path, 'r') as xml_file:
            tmx = etree.parse(xml_file, etree.XMLParser())
            body = tmx.getroot().find("body")
            for tu in body:
                sentence = None

                for i, tuv in enumerate(tu):
                    text = tuv.find("seg").text
                    if i == 0:
                        sentence = { "source": text, "target": [] }
                    else:
                        if tmx_mode == "create":
                            sentence.get('target').append(text)
                        sentence.get('target').append(self.get(user_id, text))

                sentences.append(sentence)
            
        tmx_path_translated = self.tmx_builder(user_id, sentences)
        shutil.move(tmx_path_translated, tmx_path)

    def translate_office(self, user_id, file_path, as_tmx = False):
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
                    self.translate_xml(user_id, xml_file_path, "xml", as_tmx)
            
            shutil.make_archive(filename, 'zip', extract_path, '.')
            shutil.move('{}.zip'.format(filename), file_path)
            shutil.rmtree(extract_path)

    def translate_bridge(self, user_id, file_path, original_extension, as_tmx = False):
        filename, extension = os.path.splitext(file_path)
        dest_path = filename + "." + self.format_filters[original_extension]

        convert = subprocess.Popen("soffice --convert-to {} {} --outdir {}".format(self.format_filters[original_extension],
                        file_path, os.path.dirname(dest_path)), shell=True, cwd=app.config['MUTNMT_FOLDER'], 
                        stdout=subprocess.PIPE) 
        convert.wait()

        self.translate_office(user_id, dest_path, as_tmx)

        convert = subprocess.Popen("soffice --convert-to {} {} --outdir {}".format(original_extension[1:], dest_path,
                                os.path.dirname(dest_path)), shell=True, cwd=app.config['MUTNMT_FOLDER'], stdout=subprocess.PIPE)
        convert.wait()

        os.remove(dest_path)

    def tmx_builder(self, user_id, sentences):
        engine = self.get_user_running_engine(user_id).engine
        source_lang = engine.source.code
        target_lang = engine.target.code

        with open(os.path.join(app.config['BASE_CONFIG_FOLDER'], 'base.tmx'), 'r') as tmx_file:
            tmx = etree.parse(tmx_file, etree.XMLParser())
            body = tmx.getroot().find("body")
            for sentence in sentences:
                tu = etree.Element("tu")

                tuv_source = etree.Element("tuv", { etree.QName("http://www.w3.org/XML/1998/namespace", "lang"): source_lang })
                seg_source = etree.Element("seg")
                seg_source.text = sentence.get('source')
                tuv_source.append(seg_source)
                tu.append(tuv_source)

                for target_sentence in sentence.get('target'):
                    tuv_target = etree.Element("tuv", { etree.QName("http://www.w3.org/XML/1998/namespace", "lang"): target_lang })
                    seg_target = etree.Element("seg")
                    seg_target.text = target_sentence
                    tuv_target.append(seg_target)
                    tu.append(tuv_target)

                body.append(tu)

        tmx_path = os.path.join('/tmp', '{}.{}-{}.tmx'.format(user_id, engine.source.code, engine.target.code))
        tmx.write(tmx_path, encoding="UTF-8", xml_declaration=True, pretty_print=True)
        return tmx_path

    def generate_tmx(self, user_id, text):
        sentences_raw = sent_tokenize(text)
        sentences = []
        for sentence in sentences_raw:
            sentences.append({ "source": sentence, "target": [self.get_line(user_id, sentence)] })
        return self.tmx_builder(user_id, sentences)

    def translate_file(self, user_id, file_path, as_tmx = False, tmx_mode = None):
        filename, extension = os.path.splitext(file_path)
        self.sentences[str(user_id)] = [] if as_tmx else None
        
        if extension in [".xml", ".html"]:
            self.translate_xml(user_id, file_path, extension[1:], as_tmx)
        elif extension == ".tmx":
            self.translate_tmx(user_id, file_path, tmx_mode)
        elif extension == ".txt":
            self.translate_txt(user_id, file_path, as_tmx)
        elif extension in [".rtf", ".pdf"]:
            self.translate_bridge(user_id, file_path, extension, as_tmx)
        else:
            self.translate_office(user_id, file_path, as_tmx)

        engine = self.get_user_running_engine(user_id)
        file_path_translated = '{}.{}-{}{}'.format(filename, engine.engine.source.code, engine.engine.target.code, extension)
        shutil.move(file_path, file_path_translated)
        file_path = file_path_translated

        if as_tmx:
            tmx_path = self.tmx_builder(user_id, self.sentences[str(user_id)])

            bundle_path = '{}-tmx-bundle'.format(filename)
            os.mkdir(bundle_path)

            filename, extension = os.path.splitext(file_path)
            basename = os.path.basename(filename)
            shutil.move(tmx_path, os.path.join(bundle_path, '{}.tmx'.format(basename)))
            shutil.move(file_path, os.path.join(bundle_path, '{}{}'.format(basename, extension)))
            shutil.make_archive(filename, 'zip', bundle_path, '.')
            shutil.rmtree(bundle_path)
