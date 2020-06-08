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

def filepath(folder_id, filename=None):
    if filename:
        return os.path.join(app.config[folder_id], filename)
    else:
        return app.config[folder_id]

def file_reader(file_path, start = None, offset = None):
    with open(file_path, 'r') as file:
        for i, line in enumerate(file):
            if start is not None and offset is not None:
                if i >= start and i < (start + offset):
                    yield line
            else:
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

def parse_number(number, round_number=None):
    if number == int(number):
        return int(number)
    else:
        if round_number:
            return round(number, round_number)
        else:
            return number

def format_number(number_string, abbr=False):
    number = int(number_string)

    if abbr:
        if number >= 1000000:
            return "{}M".format(parse_number(number / 1000000))
        elif number >= 1000:
            return "{}k".format(parse_number(number / 1000))
        else:
            return "{}".format(number)
    else:
        return '{:,}'.format(number)

def seconds_to_timestring(total_seconds):
    total_seconds = int(total_seconds)
    days = int(total_seconds / (24 * 3600))
    hours = int(total_seconds % (24 * 3600) / 3600)
    minutes = int(((total_seconds % (24 * 3600)) % 3600) / 60)
    seconds = int(((total_seconds % (24 * 3600)) % 3600) % 60)

    return "{}d {}h {}min {}s".format(days, hours, minutes, seconds)

def get_task_result(task, task_id):
    result = task.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return result.get()
    else:
        return None