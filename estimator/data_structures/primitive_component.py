from functools import cache

from estimator.input_handler import database_handler
from collections import OrderedDict


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
        self.comp_arguments = comp_arguments if comp_arguments else OrderedDict()
        for feature in self.scripts:
            self.scripts[feature] = database_handler.get_component_feature(self.comp_class, feature)

    def get_feature_reference_table(self, feature: str):
        """
        Get the reference table given operations + scripts, which DOES NOT involve operations dict()
        :param feature: str indicating the type of table to be printed.
        Possibilities include 'energy' 'area' 'cycle'
        :return: dict { operation : value }
        """
        values = OrderedDict({op: self.calculate_operation_stat(op, feature) for op in self.scripts[feature]})
        return values

    def calculate_operation_stat(self, operation_name: str, table_type: str,
                                      runtime_arg: OrderedDict = None) -> float:
        """
        Gets the reference stats for one operation only
        :param runtime_arg: runtime args
        :param operation_name: name of the operation
        :param table_type:  str indicating the type of table to be loaded.
        Possibilities include 'energy' 'area' 'cycle'
        :return: float value for the stat in question
        """
        runtime_arg = runtime_arg if runtime_arg else OrderedDict()
        merged_args = OrderedDict({**self.comp_arguments, **runtime_arg})
        return self.scripts[table_type][operation_name].execute(merged_args)