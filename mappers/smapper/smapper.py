from estimator.data_structures.architecture import Architecture
from estimator.data_structures.compound_component import load_compound_components
from estimator.input_handler import *
from estimator.estimator import Estimator
from mappers.smapper.wrappers import *
from mappers.smapper.solver import Solver
from mappers.smapper.operationalizer import Operationalizer
import matplotlib.pyplot as plt


class Smapper:

    def __init__(self):
        self.architecture = None
        self.nn_list = None
        self.nn = None
        self.param_cost_map = OrderedDict()
        self.top_solutions = ()

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
        n = read_yaml_file(nn_file)['neural_network'][0]
        self.nn = NeuralNetwork(n['name'], n['nn_type'], n['dimensions'], n['start'], n['end'])

    def run_operationalizer(self):
        solver = Solver(self.nn)
        op = Operationalizer(self.architecture, solver)
        op.create_operations()
        param_operations_map = op.param_operations_map
        for k, v in param_operations_map.items():
            e = Estimator(architecture=self.architecture, operations=v)
            self.param_cost_map[k] = e.estimate(["energy", "area", "cycle"], False)
        for a, b in self.param_cost_map.items():
            print("in_w, in_h, out_h, repeat:", a)
            print("pJ, um^2, cycle:", b)
            print()
        print(len(self.param_cost_map), "combinations estimated")

    def graph_energy_cycle(self):
        energy_data = tuple(math.log10(v[0]) for v in self.param_cost_map.values())
        cycle_data = tuple(math.log10(v[2]) for v in self.param_cost_map.values())
        plt.scatter(energy_data, cycle_data, marker='.')
        plt.title('Same Hardware, Different Firmware: Energy vs Cycle')
        plt.xlabel('Energy (pJ) (log10)')
        plt.ylabel('Cycles (log10)')
        plt.show()

    def print_top_solutions(self, num=10):
        # Calculated by multiplying metrics together
        self.top_solutions = sorted(((math.prod(v),v, k) for k, v in self.param_cost_map.items()))
        print('{:^25} | {:^35} | {:^20}'.format('Score', 'Metrics', 'Inputs'))

        for i in range(num):
            print(i, self.top_solutions[i])
