import itertools
from collections import OrderedDict
from copy import deepcopy

from estimator.data_structures.architecture import flatten_architecture, Architecture
from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.input_handler import database_handler
from searcher.meta_compound_component import *

"""
Outputs a range of Architecture Options from a meta_arch param
"""


class MetaArchitecture:
    def __init__(self, yaml_data: OrderedDict, meta_cc_dir=None):
        """
        Defines the Meta-Architecture, which will contain the possibility space for all the different architectures
        that are possible, given the constraints defined in the meta-architecture template.
        :param yaml_data: File path to the meta-architecture YAML file containing the definition
        :param meta_cc_dir: File path to the folder containing the meta-compound-components to be used in this
        meta-architecture
        """
        assert "meta_architecture" in yaml_data, "Not a meta-architecture template!"
        if meta_cc_dir:
            load_meta_compound_component_library(meta_cc_dir)
        yaml_data = yaml_data['meta_architecture']
        self.base_arch = Architecture()
        self.base_arch.name = yaml_data['name']
        self.base_arch.version = yaml_data['version']
        self.pc_arg_val = []  # (PC, arg, arg_array_vals)
        self.meta_cc_combs = []  # 2d array, each item is a list of meta-cc possibilities
        self.meta_cc_name_vars = [] # MCC name, MCC variables
        self.argument_combs = None
        self.param_architecture_map = None
        self.param_set_labels = []  # String tuple


        flat_arch = flatten_architecture(yaml_data)
        meta_cc_combs = []
        for item in flat_arch:
            item_name = item['name']
            item_class = item['class']
            item_arguments = item['arguments'] if 'arguments' in item else None
            # Check whether it is a primitive component or compound component
            if database_handler.is_primitive_component(item_class):
                pc = PrimitiveComponent(item_name, item_class)
                self.base_arch.component_dict[item_name] = pc
                if item_arguments:
                    self.pc_arg_val += [(pc, k, v) for k, v in item_arguments.items()]
                    self.param_set_labels += [f"hardware_{item_name}_{key}" for key in item_arguments]
            else:
                mcc = deepcopy(meta_compound_component_library[item_class])
                self.meta_cc_name_vars.append((item_name, mcc))
                meta_cc_combs.append(list(mcc.iter_compound_components()))
        self.meta_cc_combs = list(itertools.product(*meta_cc_combs))
        print(self.meta_cc_name_vars)
        print(self.param_set_labels)

    def get_param_bounds(self):
        # Used for Bayes Optim
        out_dict = {}
        for index, param_name in enumerate(self.param_set_labels):
            minima = min([c[index] for c in self.argument_combs]) #* 0.9
            maxima = max([c[index] for c in self.argument_combs]) #* 1.25
            out_dict[param_name] = (minima, maxima)
        return out_dict

    def get_mcc_param_bounds(self):
        out_dict = {name: mcc.get_param_bounds() for name, mcc in self.meta_cc_name_vars}
        return out_dict

    def load_argument_combinations(self):
        """
        Loads the different argument combinations using itertools according to the different parameters specified in
        the meta-architecture
        :return: None. Updates the self.argument_combs field
        """
        argument_pools = (p[2] if isinstance(p[2], list) else [p[2]] for p in self.pc_arg_val)
        self.argument_combs = tuple(itertools.product(*argument_pools))  # Cartesian product

    def iter_architectures(self):
        """
        Will iterate the different architecture possibilities in a given possibilities space and Cartesian product
        combinations of different changing elements
        :return: Generator object with <Architecture objects> in each iteration, representing a possible combination
        of different changing parameters
        """
        # Return generator of the same base architecture but with different param sets
        # print((tuple(self.argument_combs)))
        for param_set in self.argument_combs:
            self.update_base_arch(param_set)
            for cc_comb in self.meta_cc_combs:
                self.update_cc_from_comb(cc_comb)
                self.base_arch.clear_cache()
                yield self.base_arch

    def update_base_arch(self, param_set):
        """
        Update the base architecture from given a parameter set
        :param param_set: parameter set values (a tuple, with labels as defined in param_set_labels)
        :return: None. Will update the base_architecture
        """
        for i in range(len(self.pc_arg_val)):
            self.base_arch.config_label[self.param_set_labels[i]] = param_set[i]
            self.pc_arg_val[i][0].comp_args[self.pc_arg_val[i][1]] = param_set[i]
            self.pc_arg_val[i][0].clear_cache()

    def get_architecture(self, arch_config_dict, meta_cc_config_data=None):
        """
        Get an architecture from a given Architecture dict and relevant meta_cc_config_data
        :param arch_config_dict: Architecture dict: {config_label: config_data}
        :param meta_cc_config_data: Nested dict: {MCC_Name: {mcc_config_label: mcc_config_data} }
        :return: Architecture object: base_arch
        """
        param_set = tuple(arch_config_dict[label] for label in self.param_set_labels)
        self.update_base_arch(param_set)
        # Now update_cc_from_comb as specified in mcc_config_data
        if meta_cc_config_data:
            cc_comb = [mcc.get_compound_component(meta_cc_config_data[name]) for name, mcc in self.meta_cc_name_vars]
            self.update_cc_from_comb(cc_comb)
        return self.base_arch

    def update_cc_from_comb(self, cc_comb):
        """
        Update the compound components within the architecture given a compound component combination
        :param cc_comb: Compound Component Parameter combination,list of <Compound Component> objects
        :return: None. Updates the compound components within the base_arch, in preparation for iter_architectures
        """
        for cc_index in range(len(cc_comb)):
            name = self.meta_cc_name_vars[cc_index][0]
            self.base_arch.component_dict[name] = cc_comb[cc_index]
            self.base_arch.config_label.update(cc_comb[cc_index].config_label)