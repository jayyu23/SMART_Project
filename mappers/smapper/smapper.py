import numpy as np
from bayes_opt import BayesianOptimization

from estimator.data_structures.architecture import yaml_arch_factory
from estimator.data_structures.compound_component import load_compound_components
from estimator.input_handler import *
from estimator.estimator import Estimator
from mappers.smapper.wrappers import *
from mappers.smapper.solver import Solver
from mappers.smapper.operationalizer import Operationalizer
import matplotlib.pyplot as plt
import time

class Smapper:

    def __init__(self):
        self.architecture = None
        self.nn_list = None
        self.nn = None
        self.param_cost_map = OrderedDict()
        self.param_op_map = OrderedDict()
        self.top_solutions = ()
        self.param_labels = None
        self.bayes_model = None

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
        self.architecture = yaml_arch_factory(read_yaml_file(arch_path))

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
        self.param_op_map = op.param_operations_map
        self.param_labels = solver.param_labels

    def search_firmware(self, bayes=True, print_on=False):
        if bayes:
            b_start = time.time()
            # Conduct Bayesian optimization over the firmware possibilities
            # Set the parameter boundaries
            param_bounds = OrderedDict()
            fw_param_point_set = self.param_op_map.keys()
            for i in range(len(self.param_labels)):
                dimension_i = [p[i] for p in fw_param_point_set]
                max_i, m = max(dimension_i), min(dimension_i)
                min_i = m - 0.001 if max_i == m else m  # This is to avoid the error when putting bounds in Bayes model
                param_bounds[self.param_labels[i]] = (min_i, max_i)
            # Now apply the Bayesian model
            seed_num = round(0.01 * len(self.param_op_map))
            self.bayes_model = BayesianOptimization(f=self.__bayesian_trial,
                                                    pbounds=param_bounds,
                                                    random_state=10,
                                                    verbose=True)
            self.bayes_model.maximize(seed_num*3, seed_num, kappa=1)
            bayes_sol = self.__make_discrete_param(self.bayes_model.max['params'])
            print("Bayes Firmware Estimate:", bayes_sol, "Score of:", -1*self.bayes_model.max['target'])
            print("Bayesian Time:", time.time() - b_start)
            return bayes_sol
        else:
            e_time = time.time()
            # Conduct a linear search
            for k, v in self.param_op_map.items():
                e = Estimator(architecture=self.architecture, operations=v)
                self.param_cost_map[k] = e.estimate(["energy", "area", "cycle"], False)
            if print_on:
                for a, b in self.param_cost_map.items():
                    print("in_w, in_h, out_h:", a)
                    print("pJ, um^2, cycle:", b)
                    print()
            print(len(self.param_cost_map), "combinations estimated")
            print("Exhaustive Search Time: ", time.time() - e_time)
            self.rank_solutions(3, True)

    def __bayesian_trial(self, **kwargs):
        param_dict = OrderedDict(locals()['kwargs'])
        # Make into discrete params
        discrete_params = self.__make_discrete_param(param_dict)
        # Get the operations for this discrete param
        architecture, operations = self.architecture, self.param_op_map[discrete_params]
        estimator = Estimator(architecture, operations)
        energy, area, cycle = estimator.estimate(["energy", "area", "cycle"], analysis=False)
        return self.__firmware_score_function(energy, area, cycle)

    def __make_discrete_param(self, continuous_param_set: OrderedDict):
        """
        Turns a continuous parameter set suggested by the Bayesian Model into a discrete parameter set that
        is valid. For each value in the continuous param set
        :param continuous_param_set: The set of continuous params, size N
        :return: The parameter set made discrete, as an OrderedDict(). This will be put into **kwargs of Black Box Func
        """
        continuous_param_ordered = [continuous_param_set[i] for i in self.param_labels]
        continuous_param = np.array(tuple(continuous_param_ordered))
        distances = sorted([[self.__get_euclidean_distance(np.array(p), continuous_param), p] for p in self.param_op_map])
        # print("Continuous", tuple(continuous_param_ordered))
        # print("Discrete", distances[0][1])
        return distances[0][1]

    def __get_euclidean_distance(self, x: np.array, y: np.array):
        return np.sqrt(((x - y)**2).sum(axis=0))

    def __firmware_score_function(self, energy, area, cycle):
        return -1 * energy * area * cycle

    def graph_energy_cycle(self):
        energy_data = tuple(math.log10(v[0]) for v in self.param_cost_map.values())
        cycle_data = tuple(math.log10(v[2]) for v in self.param_cost_map.values())
        plt.scatter(energy_data, cycle_data, marker='.')
        plt.title('Same Hardware, Different Firmware: Energy vs Cycle')
        plt.xlabel('Energy (pJ) (log10)')
        plt.ylabel('Cycles (log10)')
        plt.show()

    def get_operations_from_param(self, param: tuple):
        return self.param_op_map[param]

    def rank_solutions(self, num=10, print_on=False):
        # Calculated by multiplying metrics together
        self.top_solutions = sorted(((math.prod(v), v, k) for k, v in self.param_cost_map.items()))
        if print_on:
            print('{:^25} | {:^35} | {:^20}'.format('Score', 'Metrics', 'Inputs'))

            for i in range(num):
                print(i + 1, self.top_solutions[i])
