from app import app
from app.blueprints.evaluate.evaluator import Evaluator

import subprocess

class Chrf(Evaluator):
    def get_name(self):
        return "chrF"

    def get_value(self, mt_path, ht_path):
        sacreBLEU = subprocess.Popen("cat {} | sacrebleu --metrics chrf -b {}".format(mt_path, ht_path), 
                        cwd=app.config['MUTNMT_FOLDER'], shell=True, stdout=subprocess.PIPE)

        score = sacreBLEU.stdout.readline().decode("utf-8")
        return 0, float(score), 1