from collections import OrderedDict
import math, yaml, yamlordereddictloader


class NeuralNetwork:

    def __init__(self, name, nn_type, dimensions, start, end):
        """
        Wrapper to describe a neural network
        :param name: Name of the network
        :param nn_type: Type of network (eg. DNN)
        :param dimensions: Dimension values of the NN, eg. in/out dim for DNN
        :param start: Components where the input starting information is held
        :param end: Components where the output information should be plaCED
        """
        self.name = name
        self.nn_type = nn_type
        self.dimensions = dimensions
        self.start = start
        self.end = end


class Pipeline:
    def __init__(self, pipeline_dict=None):
        self.pipeline_dict = pipeline_dict if pipeline_dict else OrderedDict({"type": "pipeline", "stages": []})

    def add_stage(self, operation, count, offset=1, stride=1):
        current_stage = OrderedDict({'operation': operation, 'count': math.ceil(count)})
        if offset != 1:
            current_stage['offset'] = math.ceil(offset)
        if stride != 1:
            current_stage['stride'] = math.ceil(stride)
        self.pipeline_dict['stages'].append(current_stage)

    def get_dict(self):
        return self.pipeline_dict


def write_yaml(data, out_path: str):
    file = open(out_path, "w")
    yaml.dump(data, file, Dumper=yamlordereddictloader.Dumper, default_flow_style=False)
    file.close()
