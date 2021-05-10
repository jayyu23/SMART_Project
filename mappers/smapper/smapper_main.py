from estimator.data_structures.architecture import Architecture
from estimator.data_structures.compound_component import load_compound_components
from estimator.input_handler import *


class Smapper:

    def __init__(self):
        self.architecture = None
        self.nn_list = None

    def set_architecture(self, arch_path, components_folder, database_table):
        if database_table:
            database_handler.set_ipcl_table(database_table)
        if components_folder:
            load_compound_components(components_folder)
        self.architecture = Architecture(read_yaml_file(arch_path))

    def set_nn(self, nn_file):
        self.nn_list = read_yaml_file(nn_file)['neural_network']
