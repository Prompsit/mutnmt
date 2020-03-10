from app import app
from app.blueprints.evaluate.evaluator import Evaluator

import subprocess

class Chrf(Evaluator):
    def get_name(self):
        return "FaKe"

    def get_value(self, mt_path, ht_path):
        return 0, 32, 100