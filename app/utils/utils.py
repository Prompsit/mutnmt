from app import app
import hashlib
import time
import tempfile
import os

class condec(object):
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # Return the function unchanged, not decorated.
            return func
        return self.decorator(func)

def hash(hashable):
    blake = hashlib.blake2b()
    for i in hashable:
        blake.update(i.encode("utf-8") if isinstance(i, str) else i)
    return blake.hexdigest()

def normname(user_id, filename):
    return hash('{}{}{}'.format(time.time(), user_id, filename))[:16]

def sub(folder_id, subfolder, filename=None):
    return os.path.join(os.path.join(app.config[folder_id], subfolder), filename if filename else "")

def filepath(folder_id, filename):
    return os.path.join(app.config[folder_id], filename)

def file_reader(file_path, start, offset):
    with open(file_path, 'r') as file:
        for i, line in enumerate(file):
            if i >= start and i < (start + offset):
                yield line

def file_length(file_path):
    with open(file_path, 'r') as file_reader:
        for i, line in enumerate(file_reader):
            pass

    return i + 1

def tmpfolder():
    return tempfile.mkdtemp(dir=app.config['TMP_FOLDER'])

def tmpfile(filename=None):
    if filename:
        return os.path.join(app.config['TMP_FOLDER'], filename)
    else:
        return tempfile.mkstemp(dir=app.config['TMP_FOLDER'])
