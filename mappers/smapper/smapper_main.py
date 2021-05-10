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
        :return: None
        """
        # Check that both architecture and nn_list not none
        assert self.architecture and self.nn_list, "Mapping requires both architecture and NN list!"
        comp_dict = self.architecture.component_dict
        out_operations_list = list()
        # Outer for loop: for each NN in the NN_list
        for n in self.nn_list:
            nn = NeuralNetwork(n['type'], n['dimensions'], n['start'], n['end'])
            # Check the starting position
            input_start, weight_start = nn.start['input'], nn.start['weights']
            print(comp_dict)
            print(comp_dict[input_start], comp_dict[weight_start])
