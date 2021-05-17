from estimator.data_structures.architecture import Architecture
from mappers.smapper.solver import Solver
from collections import OrderedDict
from mappers.smapper.wrappers import Pipeline
import math

class Operationalizer:

    def __init__(self, architecture: Architecture, solver: Solver):
        self.architecture = architecture
        self.comp_dict = architecture.component_dict
        self.solver = solver
        self.param_operations_map = OrderedDict()  # Maps the parameters to the operations
        self.operation_creation_map = {"dnn": self.__create_dnn_operations}

    def create_operations(self):
        return self.operation_creation_map[self.solver.nn.nn_type]()

    def __create_dnn_operations(self):
        nn = self.solver.nn
        for params in self.solver.factor_comb:
            in_w, in_h, out_h, repeat = params
            print(params)
            # 1. Check the in + weight SRAM size
            input_start = self.comp_dict[nn.start['input']].comp_args
            weight_start = self.comp_dict[nn.start['weights']].comp_args
            output_end = self.comp_dict[nn.end['output']].comp_args
            # Check dimensions
            if in_w * in_h > input_start['size']:
                print(f"Inputs: ({in_w}x{in_h}) greater than input buffer ({input_start['size']})")
                continue
            if in_h * out_h > weight_start['size']:
                print(f"Weights: ({in_h}x{out_h}) greater than weight buffer ({weight_start['size']}")
                continue
            if out_h * in_w > output_end['size']:
                print(f"Outputs: ({in_w}x{out_h}) greater than output buffer ({output_end['size']}")
                continue
            # Now create the corresponding operations
            # Find the bus width of the two starting units
            in_width, weight_width = int(input_start['width']), int(weight_start['width'])
            in_read_times = math.ceil(in_h * in_w / in_width)
            w_read_times = math.ceil(in_h * out_h / weight_width)
            # Get how many bits can the intmac do. 8, 16, etc from architecture,
            # through searching for intmac units in arch
            mac_info = self.architecture.get_component_class('intmac')
            mac_array_num, intmac_bits = len(mac_info), tuple(mac_info.items())[0][1].comp_args['datasize']
            pe_unit = tuple(mac_info.items())[0][0].split('.')[0]  # since the search result shows pe.mac_0
            pe_mac_ops = in_h * out_h / (mac_array_num * intmac_bits / 8)
            # Find the output destination
            out_width, out_bit = int(output_end['width']), 8
            out_write_times = out_h * in_width / out_width
            # Construct the pipeline
            dnn_pipeline = Pipeline()
            dnn_pipeline.add_stage(f"{nn.start['input']}.read()", in_read_times * repeat, offset=0)
            dnn_pipeline.add_stage(f"{nn.start['weights']}.read()", w_read_times * repeat, offset=0)
            dnn_pipeline.add_stage(f"{pe_unit}.mac()", pe_mac_ops * repeat, offset=1)
            dnn_pipeline.add_stage(f"{nn.end['output']}.write()", out_write_times * repeat, offset=out_h, stride=out_h)
            self.param_operations_map[tuple(params)] = dnn_pipeline.get_dict()
        for k, v in self.param_operations_map.items():
            print(k)
            print(v)
            print()