from app.utils import user_utils
import hashlib
import time

class condec(object):
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # Return the function unchanged, not decorated.
            return func
        return self.decorator(func)

def normname(user_id, filename):
    blake = hashlib.blake2b()
    blake.update(('{}{}{}'.format(time.time(), user_id, filename).encode("utf-8")))
    return blake.hexdigest()[:16]
