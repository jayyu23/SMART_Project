from collections import OrderedDict
from bitstring import BitArray

class Layer:
    def __init__(self, layer_yaml):
        self.__dict__.update(layer_yaml)
        self.__dict__.update({**layer_yaml['dimensions'], **layer_yaml['options']})


class Compiler:

    def __init__(self, nn_yaml: OrderedDict):
        self.__dict__.update(nn_yaml)
        self.nn_layer_list = nn_yaml['neural_network']
        self.compilable_types = {"dnn": lambda layer: self.__compile_dnn(layer)}
        self.compiled_binary = []
        self.annotations = []

    def compile(self):
        for nn_layer in self.nn_layer_list:
            layer = Layer(nn_layer)
            if layer.nn_type in self.compilable_types:
                self.compilable_types[layer.nn_type](layer)

    def __compile_dnn(self, layer):
        # SGEMM for the DNN layer
        sgemm_annotation = f"f{layer.name}.SGEMM"
        machine_code = BitArray(length=64)
        machine_code.overwrite('0b00', 0) # Because SGEMM, so '00'
        machine_code[3] = layer.bias
        machine_code[4] = layer.convert
        machine_code[6] = layer.convert
        machine_code[7] = layer.history
        weight_bit_map = {8: '000', 4: '001', 2: '010', 1: '011'}
        machine_code.overwrite(f"0b{weight_bit_map[layer.weight_bit][::-1]}", 8)
        machine_code.overwrite('0b11', 12)  # Manual mode, continue
        machine_code[15] = layer.history

        print(machine_code[8:11])
        print(machine_code[::-1])

