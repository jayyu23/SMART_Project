import os
from collections import OrderedDict
from estimator.input_handler import database_handler
from estimator.data_structures.primitive_component import PrimitiveComponent
from estimator.utils import parse_method_notation, read_yaml_file
from copy import deepcopy
from functools import cache

compound_component_library = OrderedDict()  # Ordered Dict representing all Compound Components


class CompoundComponent:
    """
    Describes a compound component. A compound component can have either primitive components or compound components
    as subcomponents
    """

    def __init__(self, yaml_data: OrderedDict):
        self.name = yaml_data['name']
        self.comp_class = yaml_data['class'] if 'class' in yaml_data else yaml_data['name']
        self.component_arguments = yaml_data['arguments'] if 'arguments' in yaml_data else OrderedDict()
        self.subcomponents = OrderedDict()
        self.operations = OrderedDict()

        for subcomponent in yaml_data['subcomponents']:
            # Determine if subcomponent is a primitive_component
            if database_handler.is_primitive_component(subcomponent['class']):
                # Get the primitive component
                sc_args = subcomponent['arguments'] if 'arguments' in subcomponent else None
                comp = PrimitiveComponent(subcomponent['name'], subcomponent['class'], sc_args)
            else:
                print("Compound Component Subcomponent Detected: %s " % subcomponent['class'])
                # Check if compound component in CCL
                assert subcomponent['class'] in compound_component_library, "Compound Component %s Not Found. Check " \
                                                                            "instance order" % subcomponent['class']
                comp = deepcopy(compound_component_library[subcomponent['class']])
                comp.name = subcomponent['name']
            self.subcomponents[comp.name] = comp
        for op in yaml_data['operations']:
            op_name = op['name']
            self.operations[op_name] = op['definition']
        # Add default idle operation
        if 'idle' not in self.operations:
            idle_op = OrderedDict(
                {'type': 'parallel', 'operations': ["%s.idle()" % sc for sc in self.subcomponents]})
            self.operations['idle'] = [idle_op]  # Since the dict value is a list of operations
        compound_component_library[self.comp_class] = self

    def get_feature_reference_table(self, table_type: str):
        """
        Returns the reference table, which DOES NOT involve operations dict(), and places it in self.reference_table
        :param table_type: str indicating the type of table to be loaded.
        Possibilities include 'energy' 'area' 'cycle'
        :return: int values for each operation dict { str operation : int value }
        """
        values = OrderedDict(
                {op_name: self.calculate_operation_stat(op_name, table_type) for op_name in self.operations})
        return values

    def calculate_operation_stat(self, operation_name: str, feature: str,
                                 runtime_arg: OrderedDict = None) -> float:
        """
        Gets the reference stats for one operation only
        :param runtime_arg: runtime args from current level
        :param operation_name: name of the operation
        :param feature:  str indicating the type of table to be loaded. Possibilities include 'energy' 'area' 'cycle'
        :return: float value for the stat in question
        """
        # Check that operation is valid
        assert operation_name in self.operations, "Invalid operation name %s" % operation_name
        runtime_arg = runtime_arg if runtime_arg else OrderedDict()
        op_def = self.operations[operation_name]
        out_value = 0
        results_array = []
        for sub_operation in op_def:
            # Setup all-component dict with default everything idle
            all_component_op_state_dict = \
                {sc: {"method": "idle", "arguments": OrderedDict()} for sc in self.subcomponents}

            # Add in non-idle values for necessary components
            def override_idle_state(sub_op, component_arguments):
                obj, method, argument = parse_method_notation(sub_op).values()
                # Check if any of the arguments are defined as a local component arg, then overwrite
                for comp_key in component_arguments:
                    for k, v in argument.items():
                        if comp_key in v:
                            argument[k] = str(v).replace(comp_key, component_arguments[comp_key])
                # Merge stored component args with operational runtime args
                # print(1, component_arguments, 2, argument, 3, runtime_arg)
                all_component_op_state_dict[obj] = {"method": method,
                                                    "arguments": OrderedDict(
                                                        {**component_arguments, **argument, **runtime_arg})}

            if sub_operation['type'] == "serial":
                override_idle_state(sub_operation['operation'], self.component_arguments)
            elif sub_operation['type'] == "parallel":
                for i in sub_operation['operations']:
                    override_idle_state(i, self.component_arguments)

            # Dict setup complete, now iterate through the dict to add result values
            for sc_name, sc_dict in all_component_op_state_dict.items():
                sc_obj = self.subcomponents[sc_name]
                result = 0
                repeat = sub_operation['operation-count'] if 'operation-count' in sub_operation else 1
                # Since both PC and CC have calculate_operation_stat
                result = sc_obj.calculate_operation_stat(sc_dict["method"], feature, sc_dict["arguments"])
                # Store everything in results array
                results_array.append(result * repeat)
            # If energy, sum. If cycle, max.
            if feature == "energy":
                out_value += sum(results_array)
            elif feature == "cycle":
                out_value += max(results_array)
            elif feature == "area":  # Since area is a constant not affected by operation, so break
                out_value = sum(results_array)
                break
        return out_value

    @cache
    def get_component_class(self, component_class):
        """
        Searches for the primitive component 'component class' within the subcomponents of the compound component.
        :param component_class: Primitive component to be searched for
        :return: Dict (name:comp) of all occurrences of this primitive component inside this component
        """
        out_dict = OrderedDict()
        for k, v in self.subcomponents.items():
            if isinstance(v, PrimitiveComponent) and v.comp_class == component_class:
                out_dict[self.name+"."+k] = v
            elif isinstance(v, CompoundComponent):
                out_dict.update(v.get_component_class(component_class))
        return out_dict


# Compound Component Loader
def load_compound_components(path="test/input/components/", instance_order_file="_instance_order.yaml"):
    """
    Will initiate CC objects in the order listed in instance_order_file
    :param path: directory containing compound components descriptions
    :param instance_order_file: A YAML folder containing a specific order to instantiate the CCs
    :return: None. Compound Components loaded in compound_component_library
    """
    cc_load_order = []
    # Detect the instance order YAML file
    if instance_order_file in os.listdir(path):
        cc_load_order = read_yaml_file(path + instance_order_file)
        print("Found instance order YAML, listing order as follows: %s" % cc_load_order)
    else:
        cc_load_order = sorted(os.listdir(path))
        print("Instance order YAML not found, initiating alphabetically: %s" % cc_load_order)

    for file in cc_load_order:
        # We assume one file one Compound Component
        yaml_data = read_yaml_file(os.path.join(path, file))
        # Check is a compound component file
        if type(yaml_data) != OrderedDict or 'compound_component' not in yaml_data:
            print("Incorrect formatting of compound component! File %s: " % file)
            continue
        CompoundComponent(yaml_data['compound_component'])
