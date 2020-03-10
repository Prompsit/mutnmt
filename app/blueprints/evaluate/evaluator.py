import abc

# Use this class to represent any kind
# of evaluation tool. As long as implements
# the abstract methods, MutNMT will be able to show
# its metrics.
 
class Evaluator(abc.ABC):

    # Returns the name of the metric
    @abc.abstractmethod
    def get_name(self) -> str:
        pass

    # Given both paths to Machine and Human translations,
    # a float value must be returned.
    @abc.abstractmethod
    def get_value(self, mt_path: str, ht_path: str) -> (float, float, float):
        pass