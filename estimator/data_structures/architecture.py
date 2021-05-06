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


def flatten_operations(operations_yaml, loop_vars={}):
    """
    Flattens the loops inside the operations yaml, ensuring that there are only serial and parallel
    :param loop_vars: Loop variables defined in the operations file, used to aid recursion. These always start with '$'
    :param operations_yaml: yaml containing all of the operations
    :return: a list of operations, flattened
    """
    # Variables within flattened loops start with $
    out_list = []

    for operation in operations_yaml:
        if operation['type'] == "loop":
            # Deal with the loop
            start, stop = operation['loop-param']['start'], operation['loop-param']['stop']
            step = operation['loop-param']['step'] if 'step' in operation['loop-param'] else 1
            loop_body = operation['loop-body']
            current_loop_variable = operation['loop-variable'] if 'loop-variable' in operation else None
            for iteration in range(start, stop, step):
                # Iterate loop body
                if current_loop_variable:
                    loop_vars[current_loop_variable] = str(iteration)
                out_list += flatten_operations(loop_body, loop_vars)
        else:
            # Is either a serial or parallel or pipeline
            new_operation = OrderedDict({**operation})
            if loop_vars:
                # Check the loop-variables
                for item in new_operation:
                    for var in loop_vars:
                        if var in str(new_operation[item]):
                            new_operation[item] = str(new_operation[item]).replace(var, loop_vars[var])
            out_list.append(new_operation)
    return out_list


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
        self.operation_list = None  # meaning it hasn't been initialized

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

    def set_operations(self, operation_dict: OrderedDict):
        """
        Sets the operations field of this architecture to a flattened version of the operation_dict.
        Flatten means that all the loops are removed, converted into either serial or parallel actions
        :param operation_dict: Operaton dict database (YAML OrderedDict)
        :return: None.
        """
        # Format check
        assert "operations" in operation_dict.keys(), "Not an operation template! " \
                                                      "Make sure there is an 'operations' key"
        self.operation_list = flatten_operations(operation_dict['operations'])

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

    def print_feature_estimation(self, feature: str, out_dir=None):
        """
        Prints out energy estimation according to ERT values and operation dict. Key algorithm for Phase 1
        :return: None
        """
        # Check if there is an operation dict available first
        assert self.operation_list is not None, "No operation count database available to conduct estimation."
        assert feature in ('energy', 'area', 'cycle'), "Error in feature definition"
        out_dir = out_dir if out_dir else "test/output/%s_estimation.txt" % feature
        csv_dir = "test/output/%s_estimation_matrix.csv" % feature
        units = {'energy': 'pJ', 'area': 'um^2', 'cycle': 'cycles'}
        arch_total_feature = 0
        # Dataframe with Rows = component, Columns = Operation, with a 'total' row at the bottom
        total_row = 'total'
        comp_op_matrix = pd.DataFrame({**{c: [v.calculate_operation_stat('idle', feature)] *
                                             len(self.operation_list) for c, v in self.component_dict.items()},
                                       total_row: [0] * len(self.operation_list)}).transpose()
        op_type_map = OrderedDict()
        out_text = ""
        out_text += get_SMART_logo() + "\n"
        out_text += "===== %s Estimation ======\n" % feature.capitalize()
        for operation_index in comp_op_matrix.columns:
            operation = self.operation_list[operation_index]
            # If is an area feature, then should not be multiplied (since area independent of operation count)
            repeat = 1 if 'operation-times' not in operation or feature == "area" else operation['operation-times']
            # Multiply by count. Eg. if component idle for 32 cycles, then total idle energy should be 32 * idle energy
            comp_op_matrix.loc[:][operation_index] *= repeat
            op_type = operation['type']
            op_type_map[operation_index] = op_type
            if op_type == "serial":
                obj, method, arg = parse_method_notation(operation['operation']).values()
                data = self.component_dict[obj].calculate_operation_stat(method, feature, arg)
                comp_op_matrix.loc[obj][operation_index] = data * repeat
                data_list = list(comp_op_matrix[:][operation_index])
                comp_op_matrix.loc[total_row][operation_index] = \
                    max(data_list) if feature == 'cycle' else sum(data_list)
            elif op_type == "parallel":
                for i in operation['operations']:
                    obj, method, arg = parse_method_notation(i).values()
                    data = self.component_dict[obj].calculate_operation_stat(method, feature, arg)
                    comp_op_matrix.loc[obj][operation_index] = data * repeat
                    data_list = list(comp_op_matrix[:][operation_index])
                    comp_op_matrix.loc[total_row][operation_index] = \
                        max(data_list) if feature == 'cycle' else sum(data_list)
            elif op_type == "pipeline":
                stages = operation['stages']
                active_cycles = {c: 0 for c in self.component_dict.keys()}
                total_cycles, total_offset = 0, 0
                for stage in stages:
                    # Calculate operation stat + Get the stage cycles first
                    obj, method, arg = parse_method_notation(stage['operation']).values()
                    data = self.component_dict[obj].calculate_operation_stat(method, feature, arg)
                    stage_cycles = data if feature == 'cycle' else \
                        self.component_dict[obj].calculate_operation_stat(method, 'cycle', arg)
                    # Unpack these parameters to calculate total cycle
                    stage_count = 1 if 'count' not in stage or feature == 'area' else stage['count']
                    stage_offset = 1 if 'offset' not in stage else stage['offset']
                    stage_stride = 1 if 'stride' not in stage else stage['stride']
                    total_offset += stage_offset
                    current_len = total_offset + (stage_stride * stage_count * stage_cycles)
                    # print(f"currentlen: {current_len}")
                    total_cycles = current_len if current_len > total_cycles else total_cycles
                    # print(total_cycles)
                    # Update the active operations
                    if active_cycles[obj] == 0:  # Currently only has idle energy
                        comp_op_matrix.loc[obj][operation_index] = int(data * stage_count)
                    else:
                        comp_op_matrix.loc[obj][operation_index] += int(data * stage_count)
                    active_cycles[obj] += stage_cycles * stage_count
                if feature == "cycle":
                    comp_op_matrix.loc[total_row][operation_index] = total_cycles
                elif feature == "energy":
                    # Add on the idle energy
                    for k, v in comp_op_matrix.iterrows():
                        if k == total_row:
                            continue
                        idle_cycles = total_cycles - active_cycles[k]
                        idle_energy = self.component_dict[k].calculate_operation_stat('idle', 'energy')
                        comp_op_matrix.loc[k][operation_index] += idle_energy * idle_cycles
                    # Calculate the sum, and place it in the total row
                    data_list = list(comp_op_matrix.loc[:][operation_index])
                    comp_op_matrix.loc[total_row][operation_index] = sum(data_list)
                elif feature == "area":
                    data_list = list(comp_op_matrix.loc[:][operation_index])
                    comp_op_matrix.loc[total_row][operation_index] = sum(data_list)

        # Component Breakdowns
        component_feature_dict = OrderedDict({k: v[0] for k, v in comp_op_matrix.iterrows()}) if feature == "area" \
            else OrderedDict({k: sum(v) for k, v in comp_op_matrix.iterrows()})
        arch_total_feature = comp_op_matrix.loc[total_row][0].sum() if feature == "area" \
            else comp_op_matrix.loc[total_row][:].sum()
        component_feature_dict.pop(total_row)  # Remove the total row
        out_text += "\n".join([f"\tComponent: {comp}\n\tValue: {val} {units[feature]}\n"
                               for comp, val in component_feature_dict.items()])
        out_text += "\n" + ("=" * 20) + "\n"
        out_text += "Total %s Estimation: %s %s" % (feature.capitalize(),
                                                    round(arch_total_feature, 5), units[feature]) + "\n"
        print(out_text)
        plot.pie(x=component_feature_dict.values(), labels=component_feature_dict.keys(), autopct='%1.1f%%')
        plot.title(f"Component Breakdown for {feature.capitalize()} (Unit: {units[feature]})")
        plot.show()

        comp_op_matrix.to_csv(csv_dir)
        write_as_file(out_text, out_dir)
