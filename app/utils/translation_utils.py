from app import app
from app.utils import user_utils
from app.utils.tokenizer import Tokenizer
from app.models import Engine
from toolwrapper import ToolWrapper
import xml.etree.ElementTree as ElementTree

import os 

class TranslationUtils:
    def __init__(self):
        self.running_joey = {}

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

    def translate_xml(self, user_id, xml_path):
        def explore_node(node):
            if node.text and node.text.strip():
                node.text = self.get(user_id, node.text)
            for child in node:
                explore_node(child)
        
        with open(xml_path, 'r') as xml_file:
            tree = ElementTree.parse(xml_file)
            explore_node(tree.getroot())

            tree.write(xml_path, encoding="UTF-8", xml_declaration=True)