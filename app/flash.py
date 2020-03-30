from flask import flash
from enum import Enum

class Flash(Enum):
    SUCCESS = 'success'
    MESSAGE = 'message'
    ERROR = 'error'
    WARNING = 'warning'

    # Issues a flash message with the corresponding category
    # @textlike is an object which can be converted to a string
    # (like an exception or a proper string)
    @staticmethod
    def issue(textlike: object, category = MESSAGE):
        flash(str(textlike), category.value)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and str(self) == str(other)
