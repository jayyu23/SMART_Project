import os
import itertools
import re
from collections import OrderedDict

from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.utils import read_yaml_file
from estimator.data_structures.compound_component import CompoundComponent
from estimator.input_handler import database_handler as db
from copy import deepcopy

"""
Meta Compound Component Describes Compound Components that are able to be searched
"""

meta_compound_component_library = OrderedDict()


def load_meta_compound_component_library(path="project_io/searcher_input/meta_components",
                                         instance_order_file="_instance_order.yaml"):
    meta_cc_load_order = []
    # Detect the instance order YAML file
    if instance_order_file in os.listdir(path):
        meta_cc_load_order = read_yaml_file(os.path.join(path, instance_order_file))
        print("Found instance order YAML, listing order as follows: %s" % meta_cc_load_order)
    else:
        meta_cc_load_order = sorted(os.listdir(path))
        print("Instance order YAML not found, initiating alphabetically: %s" % meta_cc_load_order)

    for file in meta_cc_load_order:
        yaml_data = read_yaml_file(os.path.join(path, file))
        if type(yaml_data) != OrderedDict or 'meta_compound_component' not in yaml_data:
            print("Incorrect formatting of compound component! File %s: " % file)
            continue
        # Create the Meta Compound Component
        mcc = MetaCompoundComponent(yaml_data)
        meta_compound_component_library[mcc.base_cc.comp_class] = mcc


class MetaCompoundComponent:
    def __init__(self, yaml_data: OrderedDict):
        yaml_data = yaml_data['meta_compound_component']
        self.base_cc = CompoundComponent()
        self.base_cc.name = yaml_data['name'] if 'name' in yaml_data else None
        self.base_cc.comp_class = yaml_data['class'] if 'class' in yaml_data else yaml_data['name']
        self.base_cc.component_arguments = yaml_data['arguments'] if 'arguments' in yaml_data else OrderedDict()
        self.base_cc.set_operations(yaml_data['operations'])
        self.subcomponent_var = []
        self.subcomponent_combs = []

        meta_combs = []
        # Now iterate over subcomponents
        for subcomponent in yaml_data['subcomponents']:
            sc_name, sc_class = subcomponent['name'], subcomponent['class']
            # Check if is primitive
            if db.is_primitive_component(sc_class):
                # Check if there are instances, in which case we don't initiate
                if 'instances' in subcomponent:
                    self.subcomponent_var.append([True, "instance", sc_name, sc_class])
                    ins = subcomponent['instances'] if isinstance(subcomponent['instances'], list) \
                        else [subcomponent['instances']]  # Convert to list
                    meta_combs.append(ins)
                else:
                    self.base_cc.subcomponents[sc_name] = PrimitiveComponent(sc_name, sc_class)
                # Check if there are arguments
                if 'arguments' in subcomponent:
                    print(subcomponent)
                    for a_key, a_val in subcomponent['arguments'].items():
                        self.subcomponent_var.append([True, "argument", sc_name, a_key])
                        a_val_list = a_val if isinstance(a_val, list) else [a_val]
                        meta_combs.append(a_val_list)
                # Get the subcomponent combs from meta_combs
                self.subcomponent_combs = itertools.product(*meta_combs)
            else:
                # TODO: Deal with a compound subcomponent
                pass

    def iter_compound_components(self):
        for param_set in self.subcomponent_combs:
            for p_index in range(len(param_set)):
                param_info = self.subcomponent_var[p_index]
                param_value = param_set[p_index]
                if param_info[0]: # Is primitive component
                    # Check if it is an instance or argument
                    if param_info[1] == "instance":
                        sc_name, sc_class = param_info[2], param_info[3]
                        # Remove former instances
                        key_removal = [k for k in self.base_cc.subcomponents if re.match(f"{sc_name}_[0-9*]", k)]
                        removed = [self.base_cc.subcomponents.pop(k) for k in key_removal]
                        # Initiate the instances
                        for i in range(param_value):
                            n = sc_name + "_" + str(i)
                            self.base_cc.subcomponents[n] = PrimitiveComponent(n, sc_class)
                    elif param_info[1] == "argument":
                        sc_name = param_info[2]
                        for k, v in self.base_cc.subcomponents.items():
                            if re.match(f"{sc_name}_[0-9*]", k) and isinstance(v, PrimitiveComponent):
                                v.comp_args[param_info[3]] = param_value
            yield deepcopy(self.base_cc)

