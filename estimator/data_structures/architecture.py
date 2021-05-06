from collections import OrderedDict
from estimator.utils import get_SMART_logo, write_as_file, parse_method_notation
from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.data_structures.compound_component import compound_component_library
from estimator.input_handler import database_handler
from copy import deepcopy
import pandas as pd
import matplotlib.pyplot as plot


def flatten_architecture(yaml_data):
    """
    Flatten architecture is a recursive method that traverses across subtrees in a YAML
    and searches for components. This is done by checking if an item is a 'group' or 'component'
    :param yaml_data: YAML OrderedDict to be flattened
    :return: An array of all the components within the original YAML OrderedDict
    """
    flattened_arch_array = []
    for item in yaml_data['components']:
        if item['type'] == "group":
            # Expand the components in the group
            flattened_arch_array += flatten_architecture(item)
        else:
            # Append the component
            flattened_arch_array.append(item)
    return flattened_arch_array


class Architecture:
    """
    Describes the architecture plan
    component_list contains an array of Component objects
    """

    def __init__(self, yaml_data: OrderedDict):
        # Check is an architecture template
        assert "architecture" in yaml_data.keys(), "Not an architecture template!"
        print(yaml_data['architecture'])
        self.name = yaml_data['architecture']['name']
        self.version = yaml_data['architecture']['version']
        self.component_dict = OrderedDict()  # Flattened Architecture, contains { Name : Component Object }

        # Expand subtrees
        flattened_arch = flatten_architecture(yaml_data['architecture'])
        for item in flattened_arch:
            item_name = item['name']
            item_class = item['class']
            # Check whether it is a primitive component or compound component
            if database_handler.is_primitive_component(item_class):
                self.component_dict[item_name] = PrimitiveComponent(item_name, item_class)  # Create comp
            else:
                # Find item from compound component library
                print("Not a primitive component", item)
                self.component_dict[item_name] = deepcopy(compound_component_library[item_class])


    def print_current_reference_table(self, table_type: str, print_data: bool = True):
        """
        Prints out the reference table, which DOES NOT involve operations dict()
        :param print_data: Whether to print out this database on terminal
        :param table_type: str indicating the type of table to be printed.
        Possibilities include 'energy' 'area' 'cycle'
        :return: None. Prints out on terminal.
        """
        # Only put all of the print out stuff here. Return values for primitive component as a dict ONLY
        assert table_type in ['energy', 'area', 'cycle'], "Invalid table type. Valid types: energy, area, cycle"
        out_text = ""
        units = {'energy': 'pJ', 'area': 'um^2', 'cycle': 'cycles'}
        unit = units[table_type]
        out_text += "===== %s Reference Table =====\n\n" % table_type.capitalize()
        out_text += "%s, v.%s\n\n" % (self.name, self.version)
        for c in self.component_dict.values():
            out_text += "===== Component =====\n"
            out_text += "Component Name: %s\n" % c.name
            out_text += "Component Class: %s\n" % c.comp_class
            c_values = c.get_feature_reference_table(table_type)
            for operation in c_values:
                out_text += "\tOperation: %s\n" % operation
                out_text += "\t%s: %s %s\n" % (
                    table_type.capitalize(), c_values[operation], unit)
                out_text += "\t----------\n"
        if print_data:
            print(out_text)
        write_as_file(out_text, "test/output/%s_reference_table.txt" % table_type)
