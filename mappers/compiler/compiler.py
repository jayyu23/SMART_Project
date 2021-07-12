from collections import OrderedDict
from bitstring import BitArray
import numpy as np
import time

from estimator.data_structures.architecture import Architecture
from mappers.compiler.hardware_model import *


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

    def get_hex_only(self):
        return str(self.bit_array[::-1]).replace('0x', '', 1)


class Compiler:

    def __init__(self, nn_yaml: OrderedDict, architecture: Architecture):
        self.__dict__.update(nn_yaml)
        self.memory_manager = MemoryManager(architecture)
        self.nn_layer_list = [Layer(l) for l in nn_yaml['neural_network']]
        self.compilable_types = {"dnn": lambda layer, is_last: self.__compile_dnn(layer, is_last),
                                 "fsmn": lambda layer, is_last: self.__compile_fsmn(layer)}
        self.compiled_binary = []

        # Variables set upon init
        self.tdnn_relu = tuple()
        self.fsmn_relu = tuple()
        self.fsmn_layer_left_num = 0
        self.matrix_in = 0
        self.matrix_out = 0
        self.sgemm_drop_bits = 0
        self.after_scaler_drop_bits = 0
        self.fsmn_drop_bits = 0

        # Connecting with the info from Memory Manager. These are both MemoryModel objects
        self.his_sram = self.memory_manager.get('his_sram')
        self.data_sram = self.memory_manager.get('data_sram')

        # Memory Address Information
        self.sgemm_his_addr_start = 0x400
        self.data_sram_address = 0  # Since we replace the information each time
        self.first_fsmn_start, self.first_fsmn_frame_stop = None, None  # Used for Copy His -> Data
        self.data_copy_address = 0x1000

    def compile(self):
        start_time = time.time()
        self.__compile_init()
        for layer_index, layer in enumerate(self.nn_layer_list):
            if layer.nn_type in self.compilable_types:
                self.compilable_types[layer.nn_type](layer, (layer_index + 1 == len(self.nn_layer_list)))
        print(f"Execution time: {time.time() - start_time: .6f} seconds")

    def __compile_init(self):
        # Initialize the registers at the very beginning
        # Search for TDNN + FSMN amongst layers
        tdnn_layers = [l for l in self.nn_layer_list if l.nn_type == "tdnn"]
        fsmn_layers = [l for l in self.nn_layer_list if l.nn_type == "fsmn"]
        dnn_layers = [l for l in self.nn_layer_list if l.nn_type == "dnn"]
        self.tdnn_relu = (0, 127)  # This is the default
        self.fsmn_layer_left_num = 0
        if tdnn_layers:
            raise NotImplementedError(f"TDNN Not implemented")
        if fsmn_layers:
            self.fsmn_layer_left_num = fsmn_layers[0].his_l_num
            self.fsmn_drop_bits = fsmn_layers[0].convert_drop_bits
            self.fsmn_relu = (fsmn_layers[0].relu_min, fsmn_layers[0].relu_max)
        if dnn_layers:
            self.sgemm_drop_bits = dnn_layers[0].convert_drop_bits
            self.after_scaler_drop_bits = dnn_layers[0].after_scaler_drop_bits
        self.tdnn_relu = self.tdnn_relu
        # Now write the compiled code
        # Line 1
        dsc_init_1 = DescriptorLine("init dsc_update tdnn_relu sgemm_drop_bits fsmn_layer_num")
        dsc_init_1.write('01', 1)
        dsc_init_1.write('01', 3)
        dsc_init_1.write('111', 6)
        dsc_init_1.write(np.binary_repr(self.tdnn_relu[0], 8), 15)
        dsc_init_1.write(np.binary_repr(self.tdnn_relu[1], 8), 23)
        dsc_init_1.write('0010', 27)  # SGEMM 32to8 TODO: Add in support for SGEMM_scale_drop_bits
        dsc_init_1.write(np.binary_repr(self.sgemm_drop_bits, 5), 32)
        dsc_init_1.write('0001', 47)  # His_num His_L_num
        dsc_init_1.write(np.binary_repr(self.fsmn_layer_left_num, 6), 53)  # His_num His_L_num
        dsc_init_1.write(np.binary_repr(self.fsmn_layer_left_num, 6), 61)  # His_num His_L_num

        # Line 2
        dsc_init_2 = DescriptorLine("init dsc_update bypass fsmn_relu fsmn_drop_bits")
        dsc_init_2.write('01', 1)
        dsc_init_2.write('11', 3)
        dsc_init_2.write('111', 6)
        dsc_init_2.write('0011', 27)  # his_sum 32to8 relu
        dsc_init_2.write(np.binary_repr(self.fsmn_relu[0], 8), 35)
        dsc_init_2.write(np.binary_repr(self.fsmn_relu[1], 8), 43)
        dsc_init_2.write('0101', 47)
        dsc_init_2.write(np.binary_repr(self.fsmn_drop_bits, 5), 52)

        self.compiled_binary += [dsc_init_1, dsc_init_2]

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
        self.matrix_in = layer.in_height
        in_height = np.binary_repr(layer.in_height, 13)
        update_code.write(in_height, 40)
        # DSC_UP 2
        self.matrix_out = layer.out_height
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
            his_binary = np.binary_repr(self.sgemm_his_addr_start, 13)
            his_data_bits = self.matrix_out * 8 * (self.fsmn_layer_left_num + 1)  # Times by 8 bit int datapoint
            self.prev_his_addr, self.sgemm_his_addr_start = self.memory_manager.get('his_sram') \
                .write_to_address_bits(self.sgemm_his_addr_start, his_data_bits, 'bit')
            sgemm_code.write(his_binary, 28)
        # Write memory addresses for data_sram
        sgemm_code.write(np.binary_repr(self.data_sram_address, 13), 44)
        sgemm_code.write(np.binary_repr(self.data_sram_address, 13), 60)
        # Check if last layer
        if is_last_layer:
            sgemm_code.write(1, 6)  # FSMN Mode
            sgemm_code.write(0, 13)  # Turn off continuous mode
        self.compiled_binary.append(update_code)
        self.compiled_binary.append(sgemm_code)

    def __compile_fsmn(self, layer):
        # Calculate FSMN Address
        single_layer_bits = self.matrix_out * 8
        fsmn_bits = convert_to_bits(single_layer_bits * self.fsmn_layer_left_num, 'bit')
        his_fsmn_diff = self.his_sram.get_num_address(fsmn_bits, 'bit')  # = 40
        fsmn_address = self.prev_his_addr - his_fsmn_diff
        start_address, stop_address = self.his_sram.write_to_address_bits(fsmn_address, fsmn_bits)
        if self.first_fsmn_start is None:
            # print(start_address, stop_address)
            self.first_fsmn_start = start_address
            self.first_fsmn_frame_stop = start_address + self.his_sram.get_num_address(single_layer_bits, 'bit')
        # Write FSMN Binary
        fsmn_annotation = f"{layer.name}.FSMN_his"
        fsmn_code = DescriptorLine(fsmn_annotation)
        fsmn_code.write('01', 1)
        fsmn_code.write('001', 6)  # FSMN_his
        fsmn_code.write('1', 7)   # History = 1
        fsmn_code.write('11', 13)  # Work mode = 1, continuous mode = 1

        fsmn_code.write(np.binary_repr(fsmn_address, 13), 44)
        fsmn_code.write(np.binary_repr(self.data_sram_address, 13), 60)
        self.compiled_binary.append(fsmn_code)
        # Check if is the last FSMN layer
        if layer.name == [l for l in self.nn_layer_list if l.nn_type == "fsmn"][-1].name:
            # Do the Data Move his -> data in MemoryModel
            last_his_address = self.his_sram.get_max_filled_addr() + 1
            move_length = last_his_address - self.first_fsmn_frame_stop - his_fsmn_diff  # num of addresses need to move
            move_fsmn_bits = self.his_sram.get_num_bits(move_length)
            # print(last_his_address, self.first_fsmn_frame_stop, move_length)
            self.data_sram.write_to_address_bits(self.data_copy_address, move_fsmn_bits)
            # Data Move data -> his
            self.his_sram.write_to_address_bits(self.first_fsmn_start, move_fsmn_bits)

            # Now Write Binary
            copy_code_1 = DescriptorLine("Copy His -> Data")
            copy_code_1.write('01', 1)
            copy_code_1.write('110', 6)
            copy_code_1.write('0', 8)
            copy_code_1.write('1', 13)
            copy_code_1.write(np.binary_repr(move_length, 13), 28)
            copy_code_1.write(np.binary_repr(self.data_copy_address, 13), 44)
            copy_code_1.write(np.binary_repr(self.first_fsmn_frame_stop, 13), 60)

            copy_code_2 = DescriptorLine("Copy Data -> His")
            copy_code_2.write('01', 1)
            copy_code_2.write('110', 6)
            copy_code_2.write('1', 8)
            copy_code_2.write('1', 13)
            copy_code_2.write(np.binary_repr(move_length, 13), 28)
            copy_code_2.write(np.binary_repr(self.data_copy_address, 13), 44)
            copy_code_2.write(np.binary_repr(self.first_fsmn_start, 13), 60)
            self.compiled_binary += [copy_code_1, copy_code_2]

    def write_out(self, path, comment=False):
        print(self.memory_manager)
        # Write the Annotated
        with open(path, 'w') as f:
            if comment:
                for i, c in enumerate(self.compiled_binary, start=1):
                    f.write(f"{i} {c}\n")
            else:
                for line in self.compiled_binary:
                    f.write(line.get_hex_only() + "\n")
