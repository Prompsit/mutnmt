from app.utils import user_utils
from werkzeug.utils import secure_filename
import hashlib

class condec(object):
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # Return the function unchanged, not decorated.
            return func
        return self.decorator(func)

def normname(self, user_id, filename):
    blake = hashlib.blake2b()
    blake.update(secure_filename('{}{}'.format(user_id, filename).encode("utf-8")))
    return blake.hexdigest()[:16]
