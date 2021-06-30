from collections import OrderedDict
from bitstring import BitArray
import numpy as np


class Layer:
    def __init__(self, layer_yaml):
        self.__dict__.update(layer_yaml)
        self.__dict__.update({**layer_yaml['dimensions'], **layer_yaml['options']})


class DescriptorLine:
    """
    Wrapper class around BitArray to make Descriptor lines better to edit
    """

    def __init__(self, annotation):
        self.annotation = annotation
        self.bit_array = BitArray(64)  # Since will always be 64

    def __repr__(self):
        return str(self.bit_array[::-1]) + " " + self.annotation

    def write(self, bit_values, last_index):
        if type(bit_values) == bool:
            bit_values = int(bit_values)
        bit_values = str(bit_values)
        for i, n in enumerate(bit_values):
            self.bit_array[last_index - i] = int(n)


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
        update_code = DescriptorLine(update_annotation)
        # DSC_UP 0
        update_code.write('01', 1)  # For "other" operations
        update_code.write('00', 3)  # Because our ReLU is signed integer
        update_code.write('111', 6)  # We want to do DSC_Update

        relu_min, relu_max = np.binary_repr(layer.relu_min, 8), np.binary_repr(layer.relu_max, 8)
        update_code.write(relu_min, 15)
        update_code.write(relu_max, 23)

        # DSC_UP 1
        in_height = np.binary_repr(layer.in_height, 13)
        update_code.write(in_height, 40)

        # DSC_UP 2
        out_height = np.binary_repr(layer.out_height, 13)
        update_code.write(out_height, 60)

        # SGEMM for the DNN layer
        sgemm_annotation = f"{layer.name}.SGEMM"
        sgemm_code = DescriptorLine(sgemm_annotation)
        sgemm_code.write('00', 1)  # Because SGEMM, so '00'
        sgemm_code.write(layer.bias, 3)
        sgemm_code.write(layer.convert, 4)
        sgemm_code.write(layer.convert, 6)
        sgemm_code.write(layer.history, 7)

        weight_bit_map = {8: '000', 4: '001', 2: '010', 1: '011'}
        sgemm_code.write(weight_bit_map[layer.weight_bit], 10)
        sgemm_code.write('11', 13)  # Manual mode, continue
        sgemm_code.write(layer.history, 15)
        # Check if last layer
        if is_last_layer:
            sgemm_code.write(1, 6)  # FSMN Mode
            sgemm_code.write(0, 13)  # Turn off continuous mode
        self.compiled_binary.append(update_code)
        self.compiled_binary.append(sgemm_code)
