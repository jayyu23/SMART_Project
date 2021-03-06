from functools import lru_cache
from estimator.input_handler import database_handler
from collections import OrderedDict
import time


class PrimitiveComponent:
    """
    Describes each individual primitive component.
    Scripts is a nested dict(), Feature (Energy) -> Operation (Read) -> FeatureScript
    """

    def __init__(self, name: str, comp_class: str, comp_arguments=None):
        """
        Constructor for a component object.
        :param name: The given name of the component
        :param comp_class: The class of the component. Corresponds to ComponentName in Database
        """
        self.scripts = {"energy": OrderedDict(), "area": OrderedDict(), "cycle": OrderedDict()}
        self.name = name
        self.comp_class = comp_class
        # Get the default arguments, then override
        user_args = comp_arguments if comp_arguments else OrderedDict()
        self.comp_args = OrderedDict({**database_handler.get_default_arguments(self.comp_class), **user_args})
        for feature in self.scripts:
            self.scripts[feature] = database_handler.get_component_feature(self.comp_class, feature,
                                                                           list(self.comp_args.keys()),
                                                                           list(self.comp_args.values()))
        # print(self.name, self.comp_args)

    def __repr__(self):
        return f"<{self.name} {self.comp_class} Primitive Component> {dict(self.comp_args)}"

    def get_feature_reference_table(self, feature: str):
        """
        Get the reference table given operations + scripts, which DOES NOT involve operations dict()
        :param feature: str indicating the type of table to be printed.
        Possibilities include 'energy' 'area' 'cycle'
        :return: dict { operation : value }
        """
        values = OrderedDict({op: self.calculate_operation_stat(op, feature) for op in self.scripts[feature]})
        return values

    @lru_cache(None)
    def calculate_operation_stat(self, operation_name: str, table_type: str,
                                 runtime_arg: tuple = None) -> float:
        """
        Gets the reference stats for one operation only
        :param runtime_arg: runtime args
        :param operation_name: name of the operation
        :param table_type:  str indicating the type of table to be loaded.
        Possibilities include 'energy' 'area' 'cycle'
        :return: float value for the stat in question
        """
        runtime_arg = runtime_arg if runtime_arg else tuple()
        merged_args = OrderedDict({**self.comp_args, **dict({*runtime_arg})})
        return self.scripts[table_type][operation_name].execute(merged_args)

    def clear_cache(self):
        self.calculate_operation_stat.cache_clear()
