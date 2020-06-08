from app import app, db
from app.utils import utils, user_utils
from app.models import File, Corpus_File, Corpus, User, LibraryCorpora
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.datastructures import FileStorage
from lxml import etree

import os
import subprocess
import sentencepiece as spm
import re
import datetime
import shutil

def process_upload_request(user_id, bitext_file, src_file, trg_file, src_lang, trg_lang, corpus_name, corpus_desc):
    type = "bitext" if bitext_file else "bilingual" if trg_file else "monolingual"

    def process_file(file, language, corpus, role):
        db_file = upload_file(file, language, user_id=user_id)

        if role == "source":
            corpus.source_id = language
        else:
            corpus.target_id = language
        
        db.session.add(db_file)
        corpus.corpus_files.append(Corpus_File(db_file, role=role))

        return db_file

    def process_bitext(file):
        file_name, file_extension = os.path.splitext(file.filename)
        norm_name = utils.normname(user_id=user_id, filename=file_name)
        tmp_file_fd, tmp_path = utils.tmpfile()
        file.save(tmp_path)

        if file_extension == ".tmx":
            with open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'wb') as src_file, \
            open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'wb') as trg_file, \
            open(tmp_path, 'r') as tmx_file:
                tmx = etree.parse(tmx_file, etree.XMLParser())
                body = tmx.getroot().find("body")
                for tu in body:
                    for i, tuv in enumerate(tu):
                        if i > 1: break
                        line = tuv.find("seg").text.strip()
                        dest_file = src_file if i == 0 else trg_file
                        
                        dest_file.write((line + '\n').encode('utf-8'))
        else:
            # We assume it is a TSV
            with open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'wb') as src_file, \
            open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'wb') as trg_file, \
            open(tmp_path, 'r') as tmp_file:
                for line in tmp_file:
                    cols = line.strip().split('\t')
                    src_file.write((cols[0] + '\n').encode('utf-8'))
                    trg_file.write((cols[1] + '\n').encode('utf-8'))

        src_file = open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'rb')
        trg_file = open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'rb')

        return FileStorage(src_file, filename=file.filename + "-src"), \
                FileStorage(trg_file, filename=file.filename + "-trg")

    # We create the corpus, retrieve the files and attach them to that corpus
    target_db_file = None
    try:
        corpus = Corpus(name = corpus_name, type = type, 
                    owner_id = user_id, description = corpus_desc)

        if type == "bitext":
            src_file, trg_file = process_bitext(bitext_file)
    
        source_db_file = process_file(src_file, src_lang, corpus, 'source')

        if type == "bitext" or type == "bilingual":
            target_db_file = process_file(trg_file, trg_lang, corpus, 'target')

        db.session.add(corpus)

        user = User.query.filter_by(id=user_id).first()
        user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
    except Exception as e:
        raise Exception("Something went wrong on our end... Please, try again later")

    if target_db_file:
        source_lines = utils.file_length(source_db_file.path)
        target_lines = utils.file_length(target_db_file.path)
        
        if source_lines != target_lines:
            raise Exception("Source and target file should have the same length")

    db.session.commit()

def upload_file(file, language, format="text", selected_size=None, offset=None, user_id=None):
    user_id = user_id if user_id else user_utils.get_uid()
    norm_name = utils.normname(user_id=user_id, filename=file.filename)
    path = utils.filepath('FILES_FOLDER', norm_name)

    def new_file(file, path, selected_size=None):
        # We save it
        file.seek(0)
        file.save(path)
        hash = utils.hash(file)

        if selected_size is not None:
            # We get the amount of sentences we want
            crop_path = "{}.crop".format(path)

            if offset:
                crop_proccess = subprocess.Popen("cat {} | head -n {} | head -n {} > {}".format(path, offset, selected_size, crop_path), shell=True)
                crop_proccess.wait()
            else:
                crop_proccess = subprocess.Popen("cat {} | head -n {} > {}".format(path, selected_size, crop_path), shell=True)
                crop_proccess.wait()

            os.remove(path)
            shutil.move(crop_path, path)

            with open(path, 'r') as crop_file:
                hash = utils.hash(crop_file)

        # Get file stats
        wc_output = subprocess.check_output('wc -lwc {}'.format(path), shell=True)
        wc_output_search = re.search(r'^(\s*)(\d+)(\s+)(\d+)(\s+)(\d+)(.*)$', wc_output.decode("utf-8"))
        lines, words, chars = wc_output_search.group(2),  wc_output_search.group(4),  wc_output_search.group(6)

        # Save in DB
        db_file = File(path = path, name = file.filename, language_id = language,
                        hash = hash, uploader_id = user_id,
                        lines = lines, words = words, chars = chars,
                        uploaded = datetime.datetime.utcnow())

        return db_file
    
    if selected_size is not None:
        return new_file(file, path, selected_size)
    else:
        # Could we already have it stored?
        hash = utils.hash(file)

        query = File.query.filter_by(hash = hash)
        db_file = None

        try:
            db_file = query.first()
            if db_file is None: raise NoResultFound

            # We did have it, we link a new one to the existing one instead of re-uploading
            os.link(db_file.path, path)

            db_file = File(path = path, name = file.filename, uploaded = db_file.uploaded,
                            hash = hash, uploader_id = user_id, language_id = db_file.language_id,
                            lines = db_file.lines, words = db_file.words, chars = db_file.chars)
            
        except NoResultFound:
            db_file = new_file(file, path)

        return db_file

def shuffle_sentences(corpus):
    source_files = [f.file for f in corpus.corpus_files if f.role == "source"]
    target_files = [f.file for f in corpus.corpus_files if f.role == "target"]

    # Only shuffle single file corpora
    if len(source_files) == 1 and len(target_files) == 1:
        source_file, target_file = source_files[0], target_files[0]
        
        shuff_proc = subprocess.Popen("paste {} {} | shuf > mut.{}.shuf".format(source_file.path, target_file.path, corpus.id), 
                        shell=True, cwd=app.config['TMP_FOLDER'])
        shuff_proc.wait()

        extract_source = subprocess.Popen("cat mut.{}.shuf | awk -F '\\t' '{{ print $1 }}' > {}".format(corpus.id, source_file.path), 
                        shell=True, cwd=app.config['TMP_FOLDER'])
        extract_source.wait()

        extract_target = subprocess.Popen("cat mut.{}.shuf | awk -F '\\t' '{{ print $2 }}' > {}".format(corpus.id, target_file.path), 
                        shell=True, cwd=app.config['TMP_FOLDER'])
        extract_target.wait()

        os.remove(utils.sub('TMP_FOLDER', '.', 'mut.{}.shuf'.format(corpus.id)))
    else:
        raise Exception("Corpora with multiple files cannot be shuffled")


def join_corpus_files(corpus, shuffle=False, user_id=None):
    # If a corpus has several source and target files, we need to put their contents in
    # a single file. This method shuffles and prints the contents to a new file
    user_id = user_id if user_id else user_utils.get_uid()

    source_single_file = File(path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.single.src'.format(corpus.id)), 
                        name = 'mut.{}.single.src'.format(corpus.id), 
                        uploader_id = user_id,
                        uploaded = datetime.datetime.utcnow())
            
    target_single_file = File(path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.single.trg'.format(corpus.id)), 
                    name = 'mut.{}.single.trg'.format(corpus.id), 
                    uploader_id = user_id,
                    uploaded = datetime.datetime.utcnow())

    def dump_files(files, single_file_db):
        with open(single_file_db.path, 'w') as single_file:
            for file_entry in files:
                with open(file_entry.file.path, 'r') as corpus_file:
                    for line in corpus_file:
                        single_file.write(line)

                os.remove(file_entry.file.path)

                db.session.delete(file_entry.file)
                corpus.corpus_files.remove(file_entry)
                db.session.commit()

    dump_files([f for f in corpus.corpus_files if f.role == "source"], source_single_file)
    dump_files([f for f in corpus.corpus_files if f.role == "target"], target_single_file)

    corpus.corpus_files.append(Corpus_File(source_single_file, role="source"))
    corpus.corpus_files.append(Corpus_File(target_single_file, role="target"))
    db.session.commit()

    if shuffle: shuffle_sentences(corpus)

    return corpus

def train_tokenizer(engine, corpus, vocabularySize=32000):
    model_path = os.path.join(engine.path, 'train.model')
    vocab_path = os.path.join(engine.path, 'train.vocab')

    try:
        os.stat(model_path)
        os.stat(vocab_path)
    except:
        files_list = []
        for file_entry in corpus.corpus_files:
            files_list.append(file_entry.file.path)
        files = " ".join(files_list)
        random_sample_path = utils.tmpfile(filename="{}.mut.10m".format(corpus.id))
        cat_proc = subprocess.Popen("cat {} | shuf | head -n 10000000 > {}".format(files, random_sample_path), shell=True)
        cat_proc.wait()

        train_proc = subprocess.Popen("spm_train --input={} --model_prefix=mut.{} --vocab_size={} --hard_vocab_limit=false" \
                        .format(random_sample_path, corpus.id, vocabularySize),
                        cwd=utils.filepath('TMP_FOLDER'), shell=True)
        train_proc.wait()

        shutil.move(utils.filepath('TMP_FOLDER', "mut.{}.model".format(corpus.id)), model_path)
        shutil.move(utils.filepath('TMP_FOLDER', "mut.{}.vocab".format(corpus.id)), vocab_path)
        os.remove(random_sample_path)
        
        purge_vocab = subprocess.Popen("cat {} | awk -F '\\t' '{{ print $1 }}' > {}.purged".format(vocab_path, vocab_path), shell=True)
        purge_vocab.wait()

        os.remove(vocab_path)
        shutil.move("{}.purged".format(vocab_path), vocab_path)

    return model_path, vocab_path

def tokenize(corpus, engine):
    model_path, vocab_path = os.path.join(engine.path, 'train.model'), os.path.join(engine.path, 'train.vocab')

    for entry_file in corpus.corpus_files:
        file_tok_path = '{}.mut.spe'.format(entry_file.file.path)

        try:
            os.stat(file_tok_path)
        except:
            sp = spm.SentencePieceProcessor()
            sp.Load(model_path)
            with open(file_tok_path, 'w+') as file_tok:
                with open(entry_file.file.path) as file:
                    for line in file:
                        line_encoded = sp.EncodeAsPieces(line)
                        print(" ".join(line_encoded), file=file_tok)
