from collections import OrderedDict
from bitstring import BitArray
import numpy as np

class Layer:
    def __init__(self, layer_yaml):
        self.__dict__.update(layer_yaml)
        self.__dict__.update({**layer_yaml['dimensions'], **layer_yaml['options']})


class Compiler:

    def __init__(self, nn_yaml: OrderedDict):
        self.__dict__.update(nn_yaml)
        self.nn_layer_list = nn_yaml['neural_network']
        self.compilable_types = {"dnn": lambda layer, is_last: self.__compile_dnn(layer, is_last)}
        self.compiled_binary = []
        self.annotations = []

    def compile(self):
        for layer_index, nn_layer in enumerate(self.nn_layer_list):
            layer = Layer(nn_layer)
            if layer.nn_type in self.compilable_types:
                self.compilable_types[layer.nn_type](layer, (layer_index + 1 == len(self.nn_layer_list)))

    def __compile_dnn(self, layer, is_last_layer):
        # Update for the DNN ReLU
        update_annotation = f"{layer.name}.update_relu"
        update_code = BitArray(length=64)
        # DSC_UP 0
        update_code.overwrite('0b10', 0)  # For "other" operations
        update_code.overwrite('0b00', 2)  # Because our ReLU is signed integer
        update_code.overwrite('0b111', 4)  # We want to do DSC_Update
        relu_min, relu_max = np.binary_repr(layer.relu_min, 8), np.binary_repr(layer.relu_max, 8)
        for i in range(len(relu_min)):
            update_code[15 - i] = int(relu_min[i])
            update_code[23 - i] = int(relu_max[i])
        # DSC_UP 1
        in_height = np.binary_repr(layer.in_height, 13)
        for i in range(len(in_height)):
            update_code[40 - i] = int(in_height[i])
        # DSC_UP 2
        out_height = np.binary_repr(layer.out_height, 13)
        for i in range(len(in_height)):
            update_code[60 - i] = int(out_height[i])
        # SGEMM for the DNN layer
        sgemm_annotation = f"{layer.name}.SGEMM"
        sgemm_code = BitArray(length=64)
        sgemm_code.overwrite('0b00', 0) # Because SGEMM, so '00'
        sgemm_code[3] = layer.bias
        sgemm_code[4] = layer.convert
        sgemm_code[6] = layer.convert
        sgemm_code[7] = layer.history
        weight_bit_map = {8: '000', 4: '001', 2: '010', 1: '011'}
        sgemm_code.overwrite(f"0b{weight_bit_map[layer.weight_bit][::-1]}", 8)
        sgemm_code.overwrite('0b11', 12)  # Manual mode, continue
        sgemm_code[15] = layer.history
        # Check if last layer
        if is_last_layer:
            sgemm_code[6] = 1  # FSMN Mode
            sgemm_code[13] = 0  # Turn off continuous mode
        self.compiled_binary.append((update_code[::-1], update_annotation))
        self.compiled_binary.append((sgemm_code[::-1], sgemm_annotation))

