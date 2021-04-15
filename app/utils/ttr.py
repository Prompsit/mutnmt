from app import app
from app.blueprints.evaluate.evaluator import Evaluator
from app.utils import utils

from nltk.tokenize import word_tokenize

class Ttr(object):
    def get_name(self):
        return "Lexical variety"

    def compute(self, text_file_path):
        unique_words = set()
        words = []
        with open(text_file_path, 'r') as file:
            for i, line in enumerate(file):
                words += word_tokenize(line)

        unique_words.update(words)
        ttr = (len(unique_words) / len(words)) * 100

        return 0, utils.parse_number(float(ttr), 2), 100
