from app import app
from app.blueprints.evaluate.evaluator import Evaluator
from app.utils import utils

from nltk.tokenize import word_tokenize

class Ttr(Evaluator):
    def get_name(self):
        return "Lexical variety"

    def get_value(self, mt_path, ht_path):
        unique_words = set()
        words = []
        with open(mt_path, 'r') as mt_file:
            for i, mt_line in enumerate(mt_file):
                words += word_tokenize(mt_line)

        unique_words.update(words)
        ttr = (len(unique_words) / len(words)) * 100

        return 0, utils.parse_number(float(ttr), 2), 100
