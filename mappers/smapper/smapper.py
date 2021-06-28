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
import math


def score_firmware(energy, area, cycle):
    """
    Score function dictating how we should score the cost of our firmware according to the energy, area, cycle data.
    We want to maximize the score (since our Bayesian opt method can only find maxima). Therefore need to *-1.
    :param energy: Energy data, in pJ
    :param area: Area data, in um^2
    :param cycle: Cycle data, in cycles
    :return: Score of the firmware architecture. A higher score means better architecture.
    """
    return -1 * (math.log10(energy) + math.log10(area) + math.log10(cycle))


class Smapper:
    """
    Smapper, aka. SMART Mapper, is the SMART system's firmware searcher/mapper module. Given a particular hardware
    <Architecture>, Smapper will coordinate Solver find tiling possibilities, then Operationalizer to create
    SMART Operations, then call the SMART Estimator and evaluate cost/score using the static score_firmware() method.
    The user can decide which algorithm to use to conduct the search. Currently supports linear-exhaustive search
    (keyword: "linear", recommended for users with large compute for a precise/definite answer) and a
    Bayesian-Optimization based search (keyword "bayes", recommended for users with smaller compute and limited time)
    """
    def __init__(self):
        self.architecture = None
        self.nn_list = None
        self.nn = None
        self.param_cost_map = OrderedDict()
        self.param_op_map = OrderedDict()
        self.fw_param_labels = None
        self.algorithm_map = {"bayes": self.__bayesian_optimization_search,
                              "linear": self.__linear_search}

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
        n = read_yaml_file(nn_file)['neural_network'][0]  # Currently we consider only 1 layer
        self.nn = NeuralNetwork(n['name'], n['nn_type'], n['dimensions'], n['start'], n['end'])

    def run_operationalizer(self):
        """
        Run the Operationalizer, which will populate the param_op_map for all of the different combinations identified
        in the solver.
        :return: None
        """
        solver = Solver(self.nn)
        op = Operationalizer(self.architecture, solver)
        op.create_operations()
        self.param_op_map = op.param_operations_map
        self.fw_param_labels = solver.param_labels

    def search_firmware(self, algorithm="bayes"):
        return self.algorithm_map[algorithm]()

    def __bayesian_optimization_search(self):
        """
        Employ Bayesian Optimization algorithm to search for optimal firmware solutions
        :return: tuple of len == 3: (solution_arguments, score, (energy, area, cycle))
        """
        def __bayesian_trial(**kwargs):
            """
            The 'black box function' implemented in the Bayesian Optimization method
            :param kwargs: An API for the Bayesian Optimization package used
            :return: Score of the Bayesian trial
            """
            param_dict = OrderedDict(locals()['kwargs'])
            # Make into discrete params
            discrete_params = __make_discrete_param(param_dict)
            # Get the operations for this discrete param
            architecture, operations = self.architecture, self.param_op_map[discrete_params]
            estimator = Estimator(architecture, operations)
            energy, area, cycle = estimator.estimate(["energy", "area", "cycle"], analysis=False)
            return score_firmware(energy, area, cycle)

        def __make_discrete_param(continuous_param_set: OrderedDict):
            """
            Round a continuous parameter set suggested by the Bayesian Model into a discrete parameter set that
            is valid. Uses Euclidean distance algorithm
            :param continuous_param_set: The set of continuous params, size N
            :return: The parameter set made discrete, as an OrderedDict().
            This will be put into **kwargs of Black Box Function
            """
            continuous_param_ordered = [continuous_param_set[i] for i in self.fw_param_labels]
            continuous_param = np.array(tuple(continuous_param_ordered))
            euclid_distance = lambda x, y: np.sqrt(((x - y) ** 2).sum(axis=0))
            distances = sorted([[euclid_distance(np.array(p), continuous_param), p] for p in self.param_op_map])
            return distances[0][1]

        b_start = time.time()
        # Conduct Bayesian optimization over the firmware possibilities
        # Set the parameter boundaries
        param_bounds = OrderedDict()
        fw_param_point_set = self.param_op_map.keys()
        for i in range(len(self.fw_param_labels)):
            dimension_i = [p[i] for p in fw_param_point_set]
            # Heuristic: generally large tiles are more efficient
            print()
            max_i, min_i = max(dimension_i) * 1.25, min(dimension_i) * 0.9
            param_bounds[self.fw_param_labels[i]] = (min_i, max_i)
        # Now apply the Bayesian model
        seed_num = math.ceil(len(self.param_op_map) * 0.01)
        bayes_model = BayesianOptimization(f=__bayesian_trial,
                                                pbounds=param_bounds,
                                                random_state=10,
                                                verbose=True)
        bayes_model.maximize(seed_num * 3, seed_num, kappa=1)
        bayes_score = abs(bayes_model.max['target'])
        bayes_p = __make_discrete_param(bayes_model.max['params'])
        bayes_sol = {self.fw_param_labels[i]: bayes_p[i] for i in range(len(bayes_p))}
        e = Estimator(self.architecture, self.param_op_map[bayes_p])
        bayes_eac = e.estimate(['energy', 'area', 'cycle'], analysis=False)
        # print("Bayes Firmware Estimate:", bayes_sol, "Score of:", bayes_score)
        # print("Bayesian Time:", time.time() - b_start)
        return bayes_sol, bayes_score, bayes_eac

    def __linear_search(self):
        e_time = time.time()
        # Conduct a linear search
        for k, v in self.param_op_map.items():
            estimator = Estimator(architecture=self.architecture, operations=v)
            estimation = estimator.estimate(["energy", "area", "cycle"], False)
            energy, area, cycle = estimation
            self.param_cost_map[k] = (score_firmware(energy, area, cycle), estimation)
        top_solution = max(((*v, k) for k, v in self.param_cost_map.items()))
        linear_score = abs(top_solution[0])
        linear_eac, linear_p = top_solution[1], top_solution[2]
        linear_sol = {self.fw_param_labels[i]: linear_p[i] for i in range(len(linear_p))}
        # print(len(self.param_cost_map), "combinations estimated")
        # print("Exhaustive Linear Search Time: ", time.time() - e_time)
        return linear_sol, linear_score, linear_eac

    def graph_energy_cycle(self):
        energy_data = tuple(math.log10(v[1][0]) for v in self.param_cost_map.values())
        cycle_data = tuple(math.log10(v[1][2]) for v in self.param_cost_map.values())
        plt.scatter(energy_data, cycle_data, marker='.')
        plt.title('Same Hardware, Different Firmware: Energy vs Cycle')
        plt.xlabel('Energy (pJ) (log10)')
        plt.ylabel('Cycles (log10)')
        plt.show()

    def get_operations_from_param(self, param: tuple):
        return self.param_op_map[param]