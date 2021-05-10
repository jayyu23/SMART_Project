import math

from estimator.data_structures.architecture import Architecture
from estimator.data_structures.compound_component import load_compound_components
from estimator.input_handler import *
from mappers.smapper.nn_description import NeuralNetwork

class Smapper:

    def __init__(self):
        self.architecture = None
        self.nn_list = None

    def set_architecture(self, arch_path, components_folder, database_table):
        """
        Sets up the architecture from a file path
        :param arch_path: File path of the architecture to be inited
        :param components_folder: Folder containing the compound components definition for the architecture
        :param database_table: IPCL Database Table to be used to get primitive component stats. None means default table
        :return: None
        """
        if database_table:
            database_handler.set_ipcl_table(database_table)
        if components_folder:
            load_compound_components(components_folder)
        self.architecture = Architecture(read_yaml_file(arch_path))

    def set_nn(self, nn_file):
        """
        Sets up the list of the neural network processes to be operationalized as a YAML
        :param nn_file: path of YAML file to be initialized as NN list
        :return: None
        """
        self.nn_list = read_yaml_file(nn_file)['neural_network']

    def map_nn(self):
        """
        Maps the NN according to the architecture given
        :return: Tuple: (Valid, Message), eg. (True, OperationList) or (False, ErrorMessage)
        """
        # Check that both architecture and nn_list not none
        assert self.architecture and self.nn_list, "Mapping requires both architecture and NN list!"
        out_operations_list = list()
        # Outer for loop: for each NN in the NN_list
        for n in self.nn_list:
            nn = NeuralNetwork(n['name'], n['nn_type'], n['dimensions'], n['start'], n['end'])
            if nn.nn_type == "dnn":
                result, message = self._map_dnn(nn)
                if not result:
                    print(result, message)
                    break

    def _map_dnn(self, nn: NeuralNetwork):
        comp_dict = self.architecture.component_dict
        out_op_list = []
        # Check the starting position: network dimensions fit in the start
        input_start, weight_start = comp_dict[nn.start['input']].comp_args, comp_dict[nn.start['weights']].comp_args
        in_dim, out_dim, in_bit, w_bit = nn.dimensions["in"], nn.dimensions["out"], 8, nn.dimensions['weight_bit']
        num_weights = in_dim * out_dim  # Number of total weights
        if in_dim * 8 > input_start['KBsize'] * 1024 * 8 or \
                num_weights * w_bit > weight_start['KBsize'] * 1024 * 8:
            return False, f"Network Dimensions of {nn.name} do not fit in starting memory units: " \
                          f"{tuple(nn.start.values())}."
        # Find the bus width of the two starting units
        in_width, weight_width = input_start['width'], weight_start['width']
        in_read_times = math.ceil(in_dim * in_bit / in_width)
        w_read_times = math.ceil(num_weights * w_bit / weight_width)
        # TODO: Get how many bits can the intmac do. 8, 16, etc.
        mac_array_num, intmac_bits = 8, 8

        return True, out_op_list