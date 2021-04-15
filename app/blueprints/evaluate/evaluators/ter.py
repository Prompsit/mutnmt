from app import app
from app.blueprints.evaluate.evaluator import Evaluator

import subprocess
import pyter

class Ter(Evaluator):
    def get_name(self):
        return "TER"

    def get_value(self, mt_path, ht_path):
        ter = 0.0
        with open(mt_path, 'r') as mt_file, open(ht_path, 'r') as ht_file:
            for i, (mt_line, ht_line) in enumerate(zip(mt_file, ht_file)):
                ter += pyter.ter(ht_line.split(), mt_line.split())

        ter = round((ter / (i + 1)) * 100, 2) 

        return 100.0, float(ter), 0.0
