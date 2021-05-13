from collections import OrderedDict
from functools import cache

import math
import yaml
import yamlordereddictloader


@cache
def serial_op_dict(operation, operation_times=1):
    """
    :param operation: Operation to be performed (str)
    :param operation_times: Number of times operation performed
    :return an OrderedDict() representation of the serial operation
    """
    out_dict = OrderedDict({"type": "serial", "operation": operation})
    if operation_times != 1:
        out_dict["operation-times"] = operation_times
    return out_dict


@cache
def parallel_op_dict(operation_list: tuple, operation_times=1):
    """
    :param operation_list: Operations to be performed in parallel (str[])
    :param operation_times: Number of times operation performed
    :return an OrderedDict() representation of the parallel operation
    """
    out_dict = OrderedDict({"type": "parallel", "operations": [i for i in operation_list]})
    if operation_times != 1:
        out_dict["operation-times"] = math.ceil(operation_times)
    return out_dict


@cache
def pipeline_op_dict(stage_count_arg_tuple: tuple, operation_times=1):
    out_dict = OrderedDict({"type": "pipeline", "stages": []})
    if operation_times != 1:
        out_dict["operation-times"] = int(operation_times)
    for stage in stage_count_arg_tuple:
        current_stage = OrderedDict({'operation': stage[0], 'count': math.ceil(stage[1])})
        if len(stage) == 3:
            # This means has extra arguments (ie. offset, stride)
            for arg_pair in stage[2]:
                arg, val = arg_pair
                current_stage[arg] = math.ceil(val)
        out_dict['stages'].append(current_stage)
    return out_dict


def component_arch_dict(comp_name, comp_class, arg=None):
    """
    :param comp_name: Name of the component
    :param comp_class: Class of the component
    :param arg: Tuple containing ((arg1, val1), (arg2, val2))
    :return and OrderedDict() representation of the component, to be used in architecture
    """
    out_dict = OrderedDict({"type": "component", "name": comp_name, "class": comp_class})
    if arg is not None:
        out_dict['arguments'] = OrderedDict({k[0]: k[1] for k in arg}) # Assume arg is a tuple
    return out_dict


def write_yaml(data, out_path: str):
    try:
        file = open(out_path, "w")
    except FileNotFoundError:
        file = open(out_path.split("/")[-1], "w")
        print("File Not Found Error, using backup path:", file.name)
    yaml.dump(data, file, Dumper=yamlordereddictloader.Dumper, default_flow_style=False)
    file.close()
