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
    def __init__(self, yaml_data: OrderedDict):
        assert "meta_architecture" in yaml_data, "Not a meta-architecture template!"
        load_meta_compound_component_library("project_io/searcher_input/meta_components")
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
        print(self.param_set_labels)

    def load_argument_combinations(self):
        argument_pools = (p[2] if isinstance(p[2], list) else [p[2]] for p in self.pc_arg_val)
        self.argument_combs = itertools.product(*argument_pools) # Cartesian product

    def iter_architectures(self):
        # Return generator of the same base architecture but with different param sets
        # print((tuple(self.argument_combs)))
        for param_set in self.argument_combs:
            self.update_base_arch(param_set)
            for cc_comb in self.meta_cc_combs:
                self.update_cc_from_comb(cc_comb)
                yield param_set, self.base_arch

    def update_base_arch(self, param_set):
        for i in range(len(self.pc_arg_val)):
            self.base_arch.config_label[self.param_set_labels[i]] = param_set[i]
            self.pc_arg_val[i][0].comp_args[self.pc_arg_val[i][1]] = param_set[i]
            self.pc_arg_val[i][0].clear_cache()

    def update_cc_from_comb(self, cc_comb):
        for cc_index in range(len(cc_comb)):
            name = self.meta_cc_name[cc_index]
            self.base_arch.component_dict[name] = cc_comb[cc_index]
            self.base_arch.config_label.update(cc_comb[cc_index].config_label)