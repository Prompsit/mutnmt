# Inspired in https://github.com/juliakreutzer/slack-joey/blob/master/bot.py

from torchtext import data
from torchtext.datasets import TranslationDataset

from joeynmt.helpers import load_config, get_latest_checkpoint, \
    load_checkpoint
from joeynmt.vocabulary import build_vocab
from joeynmt.model import build_model
from joeynmt.prediction import validate_on_data
from joeynmt.constants import UNK_TOKEN, EOS_TOKEN, BOS_TOKEN, PAD_TOKEN

import os
import logging

class MonoLineDataset(TranslationDataset):
    def __init__(self, line, field, **kwargs):
        examples = []
        line = line.strip()
        fields = [('src', field)]
        examples.append(data.Example.fromlist([line], fields))
        super().__init__(examples, fields, **kwargs)

class JoeyWrapper:
    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.model_path = os.path.join(engine_path, 'model')
        self.config_path = os.path.join(engine_path, 'config.yaml')
        
        # Load parameters from configuration file
        config = load_config(self.config_path)

        self.ckpt = get_latest_checkpoint(self.model_path)
        self.use_cuda = config["training"].get("use_cuda", False)
        self.level = config["data"]["level"]
        self.max_output_length = config["training"].get("max_output_length", None)
        self.lowercase = config["data"].get("lowercase", False)
        self.model = config["model"]

        # load the vocabularies
        src_vocab_file = config["training"]["model_dir"] + "/src_vocab.txt"
        trg_vocab_file = config["training"]["model_dir"] + "/trg_vocab.txt"
        self.src_vocab = build_vocab(field="src", vocab_file=src_vocab_file,
                                dataset=None, max_size=-1, min_freq=0)
        self.trg_vocab = build_vocab(field="trg", vocab_file=trg_vocab_file,
                                dataset=None, max_size=-1, min_freq=0)

        # whether to use beam search for decoding, 0: greedy decoding
        if "testing" in config.keys():
            self.beam_size = config["testing"].get("beam_size", 0)
            self.beam_alpha = config["testing"].get("alpha", -1)
        else:
            self.beam_size = 1
            self.beam_alpha = -1

        # We won't preprocess here, so:
        self.tokenizer = lambda x: x
        self.detokenizer = lambda x: x

        self.segmenter = lambda x: list(x.strip()) if self.level == "char" else lambda x: x.strip()
        
        self.logger = logging.getLogger(__name__)

    def load(self):
        # build model and load parameters into it
        model_checkpoint = load_checkpoint(self.ckpt, self.use_cuda)
        model = build_model(self.model, src_vocab=self.src_vocab, trg_vocab=self.trg_vocab)
        model.load_state_dict(model_checkpoint["model_state"])

        if self.use_cuda:
            model.cuda()

        return True

    def load_line_as_data(self, line, level, lowercase, src_vocab, trg_vocab):
        tok_fun = lambda s: list(s) if level == "char" else lambda s: s.split()

        src_field = data.Field(init_token=None, eos_token=EOS_TOKEN,  # FIXME
                            pad_token=PAD_TOKEN, tokenize=tok_fun,
                            batch_first=True, lower=lowercase,
                            unk_token=UNK_TOKEN,
                            include_lengths=True)
        trg_field = data.Field(init_token=BOS_TOKEN, eos_token=EOS_TOKEN,
                            pad_token=PAD_TOKEN, tokenize=tok_fun,
                            unk_token=UNK_TOKEN,
                            batch_first=True, lower=lowercase,
                            include_lengths=True)
        test_data = MonoLineDataset(line=line, field=(src_field))
        src_field.vocab = src_vocab
        trg_field.vocab = trg_vocab

        return test_data, src_vocab, trg_vocab

    def joey_translate(self, message_text, model, src_vocab, trg_vocab, preprocess, postprocess,
              logger, beam_size, beam_alpha, level, lowercase,
              max_output_length, use_cuda, nbest):

        sentence = message_text.strip()
        if lowercase:
            sentence = sentence.lower()
        for p in preprocess:
            sentence = p(sentence)

        # load the data which consists only of this sentence
        test_data, src_vocab, trg_vocab = self.load_line_as_data(lowercase=lowercase,
            line=sentence, src_vocab=src_vocab, trg_vocab=trg_vocab, level=level)

        # generate outputs
        score, loss, ppl, sources, sources_raw, references, hypotheses, \
        hypotheses_raw, attention_scores = validate_on_data(
            model, data=test_data, batch_size=1, level=level,
            max_output_length=max_output_length, eval_metric=None,
            use_cuda=use_cuda, loss_function=None, beam_size=beam_size,
            beam_alpha=beam_alpha, logger=logger)

        return hypotheses

    def translate(self, line, nbest=1):
        line = line.strip()
        if line:
            return self.joey_translate(line,
                            beam_size=self.beam_size,
                            beam_alpha=self.beam_alpha,
                            level=self.level,
                            lowercase=self.lowercase,
                            max_output_length=self.max_output_length,
                            model=self.model,
                            postprocess=[self.detokenizer],
                            preprocess=[self.tokenizer, self.segmenter],
                            src_vocab=self.src_vocab,
                            trg_vocab=self.trg_vocab,
                            use_cuda=self.use_cuda,
                            logger=self.logger,
                            nbest=nbest)
        else:
            return None