import os
import itertools
import re
from collections import OrderedDict
import numpy as np
from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.utils import read_yaml_file
from estimator.data_structures.compound_component import CompoundComponent
from estimator.input_handler import database_handler as db
from copy import deepcopy

"""
Meta Compound Component Describes Compound Components that are able to be searched, with parameter combinations within
the specified constraints (defined as a possibilities space)
"""

meta_compound_component_library = OrderedDict()


def load_meta_compound_component_library(path="project_io/searcher_input/meta_components",
                                         instance_order_file="_instance_order.yaml"):
    """
    Loads the meta-compound-components from a given folder, and places them into the global
    meta_compound_component_library
    :param path: Path of the compound components folder
    :param instance_order_file: File name of the _instance_order file, which describes the order in which the
    compound components should be initialized in.
    :return: None. Will Populate the meta_compound_component_library global.
    """
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
        meta_compound_component_library[mcc.base_cc.comp_class] = deepcopy(mcc)


class MetaCompoundComponent:
    """
    Class defining each meta-compound-component
    """

    def __init__(self, yaml_data: OrderedDict):
        yaml_data = yaml_data['meta_compound_component']
        self.base_cc = CompoundComponent()
        self.base_cc.name = yaml_data['name'] if 'name' in yaml_data else None
        self.base_cc.comp_class = yaml_data['class'] if 'class' in yaml_data else yaml_data['name']
        self.base_cc.component_arguments = yaml_data['arguments'] if 'arguments' in yaml_data else OrderedDict()
        self.base_cc.set_operations(yaml_data['operations'])
        self.subcomponent_var = []
        self.subcomponent_combs = []
        self.subcomponent_comb_labels = []

        meta_combs = []
        # Now iterate over subcomponents
        for subcomponent in yaml_data['subcomponents']:
            sc_name, sc_class = subcomponent['name'], subcomponent['class']
            # Check if is primitive
            if db.is_primitive_component(sc_class):
                # Check if there are instances, in which case we don't initiate
                if 'instances' in subcomponent:
                    self.subcomponent_var.append([True, "instance", sc_name, sc_class])
                    ins_num = subcomponent['instances'] if isinstance(subcomponent['instances'], list) \
                        else [subcomponent['instances']]  # Convert to list
                    meta_combs.append(ins_num)
                    self.subcomponent_comb_labels.append(f"hardware_{sc_name}_instances")
                else:
                    self.base_cc.subcomponents[sc_name] = PrimitiveComponent(sc_name, sc_class)
                # Check if there are arguments
                if 'arguments' in subcomponent:
                    for a_key, a_val in subcomponent['arguments'].items():
                        self.subcomponent_var.append([True, "argument", sc_name, a_key])
                        a_val_list = a_val if isinstance(a_val, list) else [a_val]
                        meta_combs.append(a_val_list)
                        self.subcomponent_comb_labels.append(f"hardware_{sc_name}_{a_key}")
                # Get the subcomponent combs from meta_combs
                self.subcomponent_combs = tuple(itertools.product(*meta_combs))
            else:
                # Deal with a compound subcomponent
                #  raise NotImplementedError("Compound Component Subcomponents functionality not yet implemented!")
                meta_combs = []
                mcc = deepcopy(meta_compound_component_library[sc_class])
                mcc_combs = mcc.subcomponent_combs
                self.subcomponent_comb_labels.append(f"hardware_{sc_name}_configs_" + "_".join(
                    [string.replace("hardware_", "", 1) for string in mcc.subcomponent_comb_labels]))
                meta_combs.append(mcc_combs)
                self.subcomponent_var.append([False, "subcomponents", sc_name, mcc])
                if 'instances' in subcomponent:
                    self.subcomponent_var.append([False, "instance", sc_name, mcc])
                    ins_num = subcomponent['instances'] if isinstance(subcomponent['instances'], list) \
                        else [subcomponent['instances']]
                    meta_combs.append(ins_num)
                    self.subcomponent_comb_labels.append(f"hardware_{sc_name}_instances")
                self.subcomponent_combs = tuple(itertools.product(*meta_combs))
        # print(self.subcomponent_comb_labels)

    def get_param_bounds(self):
        # Used for Bayesian Optimization
        out_dict = {}
        for index, param_name in enumerate(self.subcomponent_comb_labels):
            minima = min([c[index] for c in self.subcomponent_combs]) * 0.9
            maxima = max([c[index] for c in self.subcomponent_combs]) * 1.25
            out_dict[param_name] = (minima, maxima)
        return out_dict

    def __get_cc_from_param_set(self, param_set):
        for p_index in range(len(param_set)):
            param_info = self.subcomponent_var[p_index]
            param_value = param_set[p_index]
            if param_info[0]:  # Is primitive component
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
            else:
                sc_name, mcc = param_info[2], param_info[3]
                # We have a compound component here.
                mcc_scc = tuple(mcc.subcomponent_combs)
                if param_info[1] == "subcomponents":
                    curr_cc = next(mcc.iter_compound_components())
                    self.base_cc.subcomponents[sc_name] = curr_cc
                elif param_info[1] == "instance":
                    curr_cc = self.base_cc.subcomponents.pop(sc_name)
                    # Remove former instances
                    key_removal = [k for k in self.base_cc.subcomponents if re.match(f"{sc_name}_[0-9*]", k)]
                    removed = [self.base_cc.subcomponents.pop(k) for k in key_removal]
                    # Initiate the instances
                    for i in range(param_value):
                        n = sc_name + "_" + str(i)
                        self.base_cc.subcomponents[n] = curr_cc
            self.base_cc.config_label[self.subcomponent_comb_labels[p_index]] = param_value
        self.base_cc.clear_caches()
        return deepcopy(self.base_cc)

    def get_compound_component(self, config_dict):
        continuous_param_set = np.array(tuple(config_dict[label] for label in self.subcomponent_comb_labels))
        euclid_distance = lambda x, y: np.sqrt(((x - y) ** 2).sum(axis=0))
        discrete_param_set = sorted([(euclid_distance(continuous_param_set, p), p)
                                     for p in self.subcomponent_combs])[0][1]
        print(discrete_param_set)
        return self.__get_cc_from_param_set(discrete_param_set)

    def iter_compound_components(self):
        """
        Will iterate over the different compound component possibilities given the possibilities space and Cartesian
        product combinations of all the different changing elements.
        :return: Generator object that is a <Compound Component> at each iteration, representing a possible combination
        of the different changing parameters
        """
        for param_set in self.subcomponent_combs:
            yield self.__get_cc_from_param_set(param_set)
