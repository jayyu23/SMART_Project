from architecture_maker import ArchitectureMaker
from utils import *
from copy import deepcopy
import math

"""
Creates operations defined in the SMART Part 1 System
Helps to integrate TH NPU specifications
"""


class OperationMaker:

    def __init__(self, out_folder="smart_npu_maker/output/", mac_number=8, psram_bus_width=8, mac_bus_width=8):
        """
        Creates an Operation Maker and an Architecture Maker instance.
        :param out_folder: Output directory for Operation YAML
        :param mac_number: Number of MACs in the MAC array
        :param psram_bus_width: Number of bits that that PSRAM bus is able to transfer in one cycle
        :param mac_bus_width: Number of bits that EACH MAC bus can transfer in one cycle
        """
        self.operations = []
        self.arch_maker = ArchitectureMaker(mac_number=mac_number)
        # self.op_mappings = OrderedDict()
        self.out_folder = out_folder
        self.mac_number = mac_number
        self.psram_bus_width = psram_bus_width
        self.mac_bus_width = mac_bus_width
        self.mac_psram_ratio = math.ceil((self.mac_number * self.mac_bus_width) / self.psram_bus_width)

        # Make the compound components
        self.arch_maker.make_compound_components()
        self.arch_maker.make_npu_arch()
        # Init the mappings
        print("*Initialized Operation Maker*")

    def write_out(self):
        # Write out operations
        write_yaml(OrderedDict({"operations": self.operations}), out_path=self.out_folder + "operations.yaml")

    def add_sgemm(self, in_dim, out_dim, weight_bit, in_addr=None, out_addr=None, his_addr=None,
                  batch_mode=None, scale=None, bias=None, his_enable=None, read_psram=False):
        N, M, W, width = in_dim, out_dim, weight_bit, 64 # Width is sram_width
        psram_burst_factor = 128 * 1024 * 8
        op_times = math.ceil((in_dim * out_dim) / (self.mac_number * self.mac_bus_width / weight_bit))
        if his_enable:
            if read_psram:
                sgemm_his = deepcopy(pipeline_op_dict((("psram.setup()", N * M * W / psram_burst_factor),
                                                       ("psram.read()", N * M * W / self.psram_bus_width),
                                                       ("model_sram.write()", N * M * W / width, (("offset", 1),)),
                                                       ("data_sram.read()", N * 8 / width),
                                                       ("sgemm_sram.read()", N * M * W / width, (("offset", 1),)),
                                                       ("npu_pe.mac()", N * M / (self.mac_number * 8 / W)),
                                                       ("his_sram.write()", M * 8 / width, (("offset", 1),
                                                                                            ("stride", 1))),
                                                       )))
            else:
                sgemm_his = deepcopy(pipeline_op_dict((("data_sram.read()", N * 8 / width),
                                                       ("model_sram.read()", N * M * W / width,  (("offset", 0),)),
                                                       ("npu_pe.mac()", N * M / (self.mac_number * 8 / W)),
                                                       ("his_sram.write()", M * 8 / width, (("offset", M),
                                                                                            ("stride", M * 8 / 64))),)))
            self.operations.append(sgemm_his)
        else:
            if read_psram:
                sgemm_data = deepcopy(pipeline_op_dict((("psram.setup()", N * M * W / psram_burst_factor),
                                                       ("psram.read()", N * M * W / self.psram_bus_width),
                                                       ("model_sram.write()", N * M * W / width, (("offset", 8),)),
                                                       ("data_sram.read()", N * 8 / width),
                                                       ("model_sram.read()", N * M * W / width, (("offset", 1),)),
                                                       ("npu_pe.mac()", N * M / (self.mac_number * 8 / W)),
                                                       ("data_sram.write()", M * 8 / width, (("offset", 1),
                                                                                            ("stride", 1))),
                                                       )))
            else:
                sgemm_data = deepcopy(pipeline_op_dict((("data_sram.read()", N * 8 / width),
                                                        ("model_sram.read()", N * M * W / width, (("offset", 0),)),
                                                        ("npu_pe.mac()", N * M / (self.mac_number * 8 / W)),
                                                        ("sgemm_sram.write()", M * 8 / width, (("offset", M),
                                                                                              ("stride", M * 8 / 64))),)))
            self.operations.append(sgemm_data)

    def add_fsmn(self, out_dim, fsmn_filter_size, num_mac_array=8, read_psram=False):
        num_macs = out_dim * fsmn_filter_size
        N, layer, width = out_dim, fsmn_filter_size, 64
        psram_burst_factor = 128 * 1024 * 8
        # FSMN computes 8x8 only. It has two pipelines
        op_times = math.ceil(num_macs / num_mac_array)
        if read_psram:
            fsmn_op_dict_1 = deepcopy(pipeline_op_dict((("psram.setup()", N * layer * 8 / psram_burst_factor),
                                                       ("psram.read()", N * layer * 8 / self.psram_bus_width),
                                                       ("model_sram.write()", N * layer * 8 / width, (("offset", 8),)),
                                                       ("data_sram.read()", N * 8 / width),
                                                       ("his_sram.read()", N * layer * 8 / width),
                                                       ("model_sram.read()", N * layer * 8 / width),
                                                       ("npu_pe.mac()", N * layer * 8 / num_mac_array),
                                                       ("his_sum_sram.write()", N * layer),)),
                                                       )
            fsmn_op_dict_2 = deepcopy(pipeline_op_dict((("his_sum_sram.read()", N),
                                                        ("npu_ctrl.bitwise()", N),
                                                        ("his_sram.write()", N * 8 / width))))
        else:
            fsmn_op_dict_1 = deepcopy(pipeline_op_dict((("his_sram.read()", N * layer * 8 / width),
                                                        ("model_sram.read()", N * layer * 8 / width),
                                                        ("npu_pe.mac()", N * layer * 8 / num_mac_array),
                                                        ("his_sum_sram.write()", N * layer),)))
            fsmn_op_dict_2 = deepcopy(pipeline_op_dict((("his_sum_sram.read()", N),
                                                        ("npu_ctrl.bitwise()", N),
                                                        ("his_sram.write()", N * 8 / width))))
        self.operations += [fsmn_op_dict_1, fsmn_op_dict_2]

    def add_update_gsr(self):
        # Update the global status register
        if len(self.operations) > 0 and self.operations[-1]['type'] == "serial" and \
                self.operations[-1]['operation'] == "global_status_reg.write()":
            # This means that the last operation was also an UPDATE
            op_times = self.operations[-1]['operation-times'] if 'operation-times' in self.operations[-1] else 1
            self.operations[-1]['operation-times'] = op_times + 1
        else:
            update_op_dict = deepcopy(serial_op_dict("global_status_reg.write()"))
            self.operations.append(update_op_dict)

    def add_copy_data(self, direction_str, length):
        if "-> his" in direction_str:
            # Means copy to history
            self.operations.append(deepcopy(parallel_op_dict(("data_sram.read()", "his_sram.write()"), length * 8 / 64)))
        elif "database <-" in direction_str:
            # Means copy to database
            self.operations.append(deepcopy(parallel_op_dict(("his_sram.read()", "data_sram.write()"), length * 8 / 64)))
