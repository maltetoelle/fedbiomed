"""
Provide a way to easily to manage training arguments.
"""


from typing import Any, Dict, TypeVar, Union

from fedbiomed.common.metrics import MetricTypes
from fedbiomed.common.validator import SchemeValidator, ValidateError, \
    RuleError, validator_decorator


_MyOwnType = TypeVar("TrainingArgs")
"""
Used for type checking
"""

class TrainingArgs():
    """
    Provide a container to deal with training arguments.

    More to come...
    """
    def __init__(self, ta: Dict, grammar: Dict = None):
        """
        Create a TrainingArgs from a Dict with input validation.

        Args:
            ta:      dictionnary describing the TrainingArgs grammar.
            grammar: user provided grammar instead of default grammar

        Raises:
            ValidateError: if ta is not valid
        """
        self._ta = ta
        self._init_grammar_(grammar)

        try:
            self._sc = SchemeValidator(self._grammar)
        except RuleError:
            #
            # internal error (invalid grammar)
            raise

        # check user input
        try:
            self._sc.validate(ta)
        except (ValidateError):
            # transform to a Fed-BioMed error
            raise


    # validators
    @staticmethod
    @validator_decorator
    def _metric_validation_hook( metric: Union[MetricTypes, str, None] ):
        """
        Validate the metric argument of test_metric.
        """
        if metric is None:
            return True

        if isinstance(metric, MetricTypes):
            return True

        if isinstance(metric, str):
            metric = metric.upper()
            if metric in MetricTypes.get_all_metrics():
                return True

        return False, f"Metric {metric} is not a supported Metric"


    @staticmethod
    @validator_decorator
    def _positive_hook( v: Any):
        """
        Test if greater than 0
        """
        return v >= 0


    # grammar definition of trainnig args
    def _init_grammar_(self, grammar: Dict):
        """
        """
        if grammar is not None:
            self._grammar = grammar
            return

        self._grammar = {
            # loss rate
            "lr": {
                "rules": [ float, self._positive_hook ],
                "required": False,
                "default": 0.01
            },

            # batch_size
            "batch_size": {
                "rules": [ int ],
                "required": False,
                "default": 48
            },

            # epochs
            "epochs": {
                "rules": [ int ],
                "required": True,
                "default": 1
            },

            # dry_run
            "dry_run": {
                "rules": [ bool ],
                "required": False,
                "default": False
            },

            # batch_maxnum
            "batch_maxnum": {
                "rules": [ int ],
                "required": False,
                "default": 100
            },

            # test_ratio
            "test_ratio": {
                "rules": [ float ],
                "required": False,
                "default": 0.0
            },

            # test_on_local_updates
            "test_on_local_updates": {
                "rules": [ bool ],
                "required": False,
                "default": False
            },

            # tests_on_globals_updates
            "test_on_globals_updates": {
                "rules": [ bool ],
                "required": False,
                "default": False
            },

            # test_metric
            "test_metric": {
                "rules": [ self._metric_validation_hook ],
                "required": False
            },

            # test_metric_args (no test)
            "test_metric_args": {
                "rules": [ lambda a: True ],
                "required": False
            }

        }




    def __repr__(self):
        """
        Display the Training_Args content.
        """
        return str(self._ta)


    def __setitem__(self, key: str, value: Any) -> Any:
        """
        Validate and then set a value for a given key.

        Args:
            key:   key
            value: values

        Returns:
            validated keys

        Raises:
            ValidateError: in case of problem (invalid key or value)
        """

        try:
            self._ta[key] = value
            self._sc.validate(self._ta)
        except (RuleError, ValidateError):
            #
            # transform to FedbiomedError
            raise
        return self._ta[key]


    def modify(self, values: Dict) -> _MyOwnType:
        """
        Modify multiple keys of the trainig arguments.
        """

        for k in values:
            self.__setitem__(k, values[k])

        return self
