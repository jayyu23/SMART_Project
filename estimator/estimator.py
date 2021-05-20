from collections import OrderedDict
from copy import deepcopy
import pandas as pd
import matplotlib.pyplot as plot

from estimator.data_structures.architecture import Architecture
from estimator.data_structures.compound_component import load_compound_components
from estimator.input_handler import *

# DEFAULT_DB_PATH = "estimator/database/intelligent_primitive_component_library.db"


OUT_DIR = "project_io/estimation_output/"


def estimator_factory(arch_path: str, op_path: str, db_table, components_folder):
    # Primitive Components in IPCL
    if db_table:
        database_handler.set_ipcl_table(db_table)
    # Compound Components in CC Folder
    if components_folder:
        load_compound_components(components_folder)
    # Architecture + Operations from two files
    architecture = Architecture(read_yaml_file(arch_path))
    operation_list = read_yaml_file(op_path)#['operations']
    return Estimator(architecture, operation_list)

class Estimator:

    def __init__(self, architecture: Architecture, operations: list):
        """
        The user parses in objects instead of filepaths
        :param architecture: Architecture object to conduct estimation
        :param operations: Operations list
        """
        self.architecture = architecture
        self.operation_list = operations

    def estimate(self, features: list, analysis=True):
        # print(database_handler.table)
        out = []
        for f in features:
            out.append(self.__estimate_feature(f, OUT_DIR, analysis))
        return tuple(out)

    def __estimate_feature(self, feature: str, out_dir, analysis=True):
        """
        Prints out energy estimation according to ERT values and operation dict. Key algorithm for Phase 1
        :return: None
        """
        # Check if there is an operation dict available first
        assert self.operation_list is not None, "No operation count database available to conduct estimation."
        assert feature in ('energy', 'area', 'cycle'), "Error in feature definition"
        component_dict = self.architecture.component_dict
        out_file = out_dir + "%s_estimation.txt" % feature
        csv_dir = out_dir + "/%s_estimation_matrix.csv" % feature
        units = {'energy': 'pJ', 'area': 'um^2', 'cycle': 'cycles'}
        arch_total_feature = 0
        # Dataframe with Rows = component, Columns = Operation, with a 'total' row at the bottom
        total_row = 'total'
        comp_op_matrix = pd.DataFrame({**{c: [v.calculate_operation_stat('idle', feature)] *
                                             len(self.operation_list) for c, v in component_dict.items()},
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
                data = component_dict[obj].calculate_operation_stat(method, feature, tuple(arg.items()))
                comp_op_matrix.loc[obj][operation_index] = data * repeat
                data_list = list(comp_op_matrix[:][operation_index])
                comp_op_matrix.loc[total_row][operation_index] = \
                    max(data_list) if feature == 'cycle' else sum(data_list)
            elif op_type == "parallel":
                for i in operation['operations']:
                    obj, method, arg = parse_method_notation(i).values()
                    data = component_dict[obj].calculate_operation_stat(method, feature, tuple(arg.items()))
                    comp_op_matrix.loc[obj][operation_index] = data * repeat
                    data_list = list(comp_op_matrix[:][operation_index])
                    comp_op_matrix.loc[total_row][operation_index] = \
                        max(data_list) if feature == 'cycle' else sum(data_list)
            elif op_type == "pipeline":
                stages = operation['stages']
                active_cycles = {c: 0 for c in component_dict.keys()}
                total_cycles, total_offset = 0, 0
                for stage in stages:
                    # Calculate operation stat + Get the stage cycles first
                    obj, method, arg = parse_method_notation(stage['operation']).values()
                    data = component_dict[obj].calculate_operation_stat(method, feature, tuple(arg.items()))
                    stage_cycles = data if feature == 'cycle' else \
                        component_dict[obj].calculate_operation_stat(method, 'cycle', tuple(arg.items()))
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
                        comp_op_matrix.loc[obj][operation_index] = int(data * stage_count) * repeat
                    else:
                        comp_op_matrix.loc[obj][operation_index] += int(data * stage_count) * repeat
                    active_cycles[obj] += stage_cycles * stage_count
                if feature == "cycle":
                    comp_op_matrix.loc[total_row][operation_index] = total_cycles * repeat
                elif feature == "energy":
                    # Add on the idle energy
                    for k, v in comp_op_matrix.iterrows():
                        if k == total_row:
                            continue
                        idle_cycles = total_cycles - active_cycles[k]
                        idle_energy = component_dict[k].calculate_operation_stat('idle', 'energy')
                        comp_op_matrix.loc[k][operation_index] += idle_energy * idle_cycles * repeat
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
        if analysis:
            print(out_text)
            plot.pie(x=component_feature_dict.values(), labels=component_feature_dict.keys(), autopct='%1.1f%%')
            plot.title(f"Component Breakdown for {feature.capitalize()} (Unit: {units[feature]})")
            plot.show()

            comp_op_matrix.to_csv(csv_dir)
            write_as_file(out_text, out_file)
        return arch_total_feature
