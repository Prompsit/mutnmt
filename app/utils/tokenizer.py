from app import app
import sentencepiece as spm
import os
import subprocess


class Tokenizer:
    def __init__(self, engine):
        self.sp = None
        self.loaded = False

        # Get absolute path for engine
        realpath = subprocess.Popen("realpath {}".format(engine.path), 
                    shell=True, cwd=app.config['JOEYNMT_FOLDER'], stdout=subprocess.PIPE)
        self.path = realpath.stdout.readline().rstrip().decode("utf-8")

    def load(self):
        if not self.sp:
            self.sp = spm.SentencePieceProcessor()
            self.loaded = self.sp.Load(os.path.join(self.path, "train.model"))
            
    def tokenize(self, text):
        if self.sp:
            return " ".join(self.sp.EncodeAsPieces(text))
        return None

    def detokenize(self, text):
        if self.sp:
            tokenized = text.split(" ")
            return self.sp.DecodePieces(tokenized)
        return None