import itertools
from collections import OrderedDict
from copy import deepcopy

from estimator.data_structures.architecture import flatten_architecture, Architecture
from estimator.data_structures.compound_component import compound_component_library, load_compound_components
from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.input_handler import database_handler

"""
Outputs a range of Architecture Options from a meta_arch param
"""


class MetaArchitecture:
    def __init__(self, yaml_data: OrderedDict):
        assert "meta_architecture" in yaml_data, "Not a meta-architecture template!"
        load_compound_components("project_io/mapper_input/components/")
        yaml_data = yaml_data['meta_architecture']
        self.base_arch = Architecture()
        self.base_arch.name = yaml_data['name']
        self.base_arch.version = yaml_data['version']
        self.pc_arg_val = []  # (PC, arg, arg_array_vals)
        self.argument_combs = None
        self.param_architecture_map = None

        flat_arch = flatten_architecture(yaml_data)
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
            else: # TODO: Fix CC for PEs
                self.base_arch.component_dict[item_name] = deepcopy(compound_component_library[item_class])
                self.base_arch.component_dict[item_name].name = item_name

    def load_argument_combinations(self):
        argument_pools = (p[2] if isinstance(p[2], list) else [p[2]] for p in self.pc_arg_val)
        self.argument_combs = itertools.product(*argument_pools) # Cartesian product

    def iter_architectures(self):
        # Return generator of the same base architecture but with different param sets
        for param_set in self.argument_combs:
            for i in range(len(self.pc_arg_val)):
                self.pc_arg_val[i][0].comp_args[self.pc_arg_val[i][1]] = param_set[i]
                self.pc_arg_val[i][0].clear_cache()
            yield param_set, self.base_arch
