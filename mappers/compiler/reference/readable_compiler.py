from collections import OrderedDict
from bitstring import BitArray
import numpy as np
import time
from mappers.smapper.wrappers import write_yaml
import json

class Layer:
    def __init__(self, layer_yaml):
        self.__dict__.update(layer_yaml)
        self.__dict__.update({**layer_yaml['dimensions'], **layer_yaml['options']})

class ReadableCompiler:

    def __init__(self, nn_yaml: OrderedDict):
        self.__dict__.update(nn_yaml)
        self.nn_layer_list = nn_yaml['neural_network']
        self.compilable_types = {"dnn": lambda layer, is_last: self.__compile_dnn(layer, is_last),
                                 "fsmn": lambda layer, is_last: self.__compile_fsmn(layer)}
        self.compiled_code = []

        # Memory Address "Magic Constants" to be edited
        self.his_addr = 0x908
        self.his_length = 44
        self.his_diff = 40
        self.fsmn_his_addr = self.his_addr - self.his_diff
        self.data_sram_start = 0
        self.data_sram_end = 0

    def compile(self):
        start_time = time.time()
        for layer_index, nn_layer in enumerate(self.nn_layer_list):
            layer = Layer(nn_layer)
            if layer.nn_type in self.compilable_types:
                self.compilable_types[layer.nn_type](layer, (layer_index + 1 == len(self.nn_layer_list)))
        print(f"Execution time: {time.time() - start_time: .6f} seconds")

    def __compile_dnn(self, layer, is_last_layer):
        # Update for the DNN ReLU
        relu_dict = OrderedDict()
        action_type = "update_sgemm_relu"
        relu_dict['name'] = f"{layer.name}.{action_type}"
        relu_dict['action_type'] = action_type
        relu_parameters = OrderedDict()
        relu_parameters['relu_min'] = layer.relu_min
        relu_parameters['relu_max'] = layer.relu_max
        relu_parameters['in_height'] = layer.in_height
        relu_parameters['out_height'] = layer.out_height
        relu_dict['parameters'] = relu_parameters

        action_type = "sgemm_operation"
        sgemm_dict = OrderedDict()
        sgemm_dict['name'] = f"{layer.name}.{action_type}"
        sgemm_dict['action_type'] = action_type
        sgemm_dict['convert_32to8'] = layer.convert
        sgemm_dict['bias'] = layer.bias
        sgemm_dict['history'] = layer.history
        # Deal with history
        if layer.history:
            sgemm_dict['his_addr'] = self.his_addr
            self.fsmn_his_addr = self.his_addr - self.his_diff
            self.his_addr += self.his_length
        # Write memory addresses for data_sram
        sgemm_dict['data_sram_start'] = self.data_sram_start
        sgemm_dict['data_sram_end'] = self.data_sram_end
        self.compiled_code += [relu_dict, sgemm_dict]

    def __compile_fsmn(self, layer):
        # Write FSMN
        fsmn_dict = OrderedDict()
        fsmn_dict['name'] = f"{layer.name}.FSMN_his"
        fsmn_dict['fsmn_his_addr'] = self.fsmn_his_addr
        fsmn_dict['fsmn_data_addr'] = self.data_sram_end
        self.compiled_code.append(fsmn_dict)

    def write_out(self, path):
        write_yaml({"compiled_code": self.compiled_code}, path)
        return
        with open(path, 'w') as f:
            f.write(json.dumps({"compiled_code": self.compiled_code}, indent=2))

