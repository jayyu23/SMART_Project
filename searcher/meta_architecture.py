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
        self.meta_cc_name = [] # MCC name, MCC variables
        self.argument_combs = None
        self.param_architecture_map = None
        self.param_set_labels = [] # String tuple

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
                self.meta_cc_name.append(item_name)
                meta_cc_combs.append(list(mcc.iter_compound_components()))
        self.meta_cc_combs = list(itertools.product(*meta_cc_combs))

    def load_argument_combinations(self):
        """
        Loads the different argument combinations using itertools according to the different parameters specified in
        the meta-architecture
        :return: None. Updates the self.argument_combs field
        """
        argument_pools = (p[2] if isinstance(p[2], list) else [p[2]] for p in self.pc_arg_val)
        self.argument_combs = itertools.product(*argument_pools) # Cartesian product

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

    def update_cc_from_comb(self, cc_comb):
        """
        Update the compound components within the architecture given a compound component combination
        :param cc_comb: Compound Component Parameter combination
        :return: None. Updates the compound components within the base_arch, in preparation for iter_architectures
        """
        for cc_index in range(len(cc_comb)):
            name = self.meta_cc_name[cc_index]
            self.base_arch.component_dict[name] = cc_comb[cc_index]
            self.base_arch.config_label.update(cc_comb[cc_index].config_label)