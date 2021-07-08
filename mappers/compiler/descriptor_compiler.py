from collections import OrderedDict
from bitstring import BitArray
import numpy as np
import time


class Layer:
    def __init__(self, layer_yaml):
        self.__dict__.update(layer_yaml)
        self.__dict__.update({**layer_yaml['dimensions'], **layer_yaml['options']})


class DescriptorLine:
    """
    Wrapper class around BitArray to make Descriptor lines better to edit
    """

    def __init__(self, annotation, line_size=64):  # Default line size 64 bits
        self.annotation = annotation
        self.bit_array = BitArray(line_size)

    def __repr__(self):
        return str(self.bit_array[::-1]) + " " + self.annotation

    def write(self, bit_values, last_index):
        bit_values = int(bit_values) if isinstance(bit_values, bool) else bit_values
        for i, n in enumerate(str(bit_values)):
            self.bit_array[last_index - i] = int(n)


class DescriptorCompiler:

    def __init__(self, nn_yaml: OrderedDict):
        self.__dict__.update(nn_yaml)
        self.nn_layer_list = [Layer(l) for l in nn_yaml['neural_network']]
        self.compilable_types = {"dnn": lambda layer, is_last: self.__compile_dnn(layer, is_last),
                                 "fsmn": lambda layer, is_last: self.__compile_fsmn(layer)}
        self.compiled_binary = []

        # Variables set upon init
        self.tdnn_relu = tuple()
        self.fsmn_layer_left_num = int()

        # Memory Address "Magic Constants" to be edited
        self.his_addr = 0x908
        self.his_length = 44
        self.his_diff = 40
        self.fsmn_his_addr = self.his_addr - self.his_diff
        self.data_sram_start = 0
        self.data_sram_end = 0

    def compile(self):
        start_time = time.time()
        for layer_index, layer in enumerate(self.nn_layer_list):
            if layer.nn_type in self.compilable_types:
                self.compilable_types[layer.nn_type](layer, (layer_index + 1 == len(self.nn_layer_list)))
        print(f"Execution time: {time.time() - start_time: .6f} seconds")

    def __compile_init(self):
        # Initialize the registers at the very beginning
        # Search for TDNN + FSMN amongst layers
        tdnn_layers = [l for l in self.nn_layer_list if l.nn_type == "tdnn"]
        fsmn_layers = [l for l in self.nn_layer_list if l.nn_type == "fsmn"]
        tdnn_relu = (0, 127)  # This is the default
        fsmn_layer_left_num = 0
        if tdnn_layers:
            raise NotImplementedError(f"TDNN Not implemented")
        if fsmn_layers:
            fsmn_layer_left_num = fsmn_layers[0].his_l_num
        self.tdnn_relu = self.tdnn_relu
        self.fsmn_layer_left_num = fsmn_layer_left_num
        # Now write the compiled code
        fsmn_tdnn

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
        # Deal with history
        if layer.history:
            his_binary = np.binary_repr(self.his_addr, 13)
            sgemm_code.write(his_binary, 28)
            self.fsmn_his_addr = self.his_addr - self.his_diff
            self.his_addr += self.his_length
        # Write memory addresses for data_sram
        sgemm_code.write(np.binary_repr(self.data_sram_start, 13), 44)
        sgemm_code.write(np.binary_repr(self.data_sram_end, 13), 60)
        # Check if last layer
        if is_last_layer:
            sgemm_code.write(1, 6)  # FSMN Mode
            sgemm_code.write(0, 13)  # Turn off continuous mode
        self.compiled_binary.append(update_code)
        self.compiled_binary.append(sgemm_code)

    def __compile_fsmn(self, layer):
        # Write FSMN
        fsmn_annotation = f"{layer.name}.FSMN_his"
        fsmn_code = DescriptorLine(fsmn_annotation)
        fsmn_code.write('01', 1)
        fsmn_code.write('001', 6)  # FSMN_his
        fsmn_code.write('1', 7)   # History = 1
        fsmn_code.write('11', 13)  # Work mode = 1, continuous mode = 1
        # Write address
        fsmn_code.write(np.binary_repr(self.fsmn_his_addr, 13), 44)
        fsmn_code.write(np.binary_repr(self.data_sram_end, 13), 60)
        self.compiled_binary.append(fsmn_code)

    def write_out(self, path):
        with open(path, 'w') as f:
            for i, c in enumerate(self.compiled_binary, start=1):
                f.write(f"{i} {c}\n")
