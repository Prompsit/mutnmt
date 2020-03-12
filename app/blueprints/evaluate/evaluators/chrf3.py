from app import app
from app.blueprints.evaluate.evaluator import Evaluator
from collections import defaultdict

import subprocess

class Chrf3(Evaluator):
    def get_name(self):
        return "chrF3"

    def get_value(self, mt_path, ht_path):
        def extract_ngrams(words, max_length=4, spaces=False):
            if not spaces:
                words = ''.join(words.split())
            else:
                words = words.strip()

            results = defaultdict(lambda: defaultdict(int))
            for length in range(max_length):
                for start_pos in range(len(words)):
                    end_pos = start_pos + length + 1
                    if end_pos <= len(words):
                        results[length][tuple(words[start_pos: end_pos])] += 1
            return results

        def get_correct(ngrams_ref, ngrams_test, correct, total):
            for rank in ngrams_test:
                for chain in ngrams_test[rank]:
                    total[rank] += ngrams_test[rank][chain]
                    if chain in ngrams_ref[rank]:
                        correct[rank] += min(ngrams_test[rank][chain], ngrams_ref[rank][chain])

            return correct, total

        def f1(correct, total_hyp, total_ref, max_length, beta=3, smooth=0):

            precision = 0
            recall = 0

            for i in range(max_length):
                if total_hyp[i] + smooth and total_ref[i] + smooth:
                    precision += (correct[i] + smooth) / (total_hyp[i] + smooth)
                    recall += (correct[i] + smooth) / (total_ref[i] + smooth)

            precision /= float(max_length)
            recall /= float(max_length)

            return (1 + beta**2) * (precision*recall) / ((beta**2 * precision) + recall), precision, recall

        ref = open(ht_path, "r")
        hyp = open(mt_path, "r")

        correct = [0]*6
        total = [0]*6
        total_ref = [0]*6

        for line in ref:
            line2 = hyp.readline()

            ngrams_ref = extract_ngrams(line, max_length=6, spaces=False)
            ngrams_test = extract_ngrams(line2, max_length=6, spaces=False)

            get_correct(ngrams_ref, ngrams_test, correct, total)

            for rank in ngrams_ref:
                for chain in ngrams_ref[rank]:
                    total_ref[rank] += ngrams_ref[rank][chain]

        chrf, precision, recall = f1(correct, total, total_ref, 6, 3)
        
        return 0, round(float(chrf*100), 2), 100
