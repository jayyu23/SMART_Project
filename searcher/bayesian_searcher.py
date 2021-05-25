from searcher.searcher import yaml_searcher_factory
from collections import OrderedDict
from bayes_opt import BayesianOptimization
from estimator.estimator import Estimator
import itertools
"""
Bayesian Optimization of the Black Box Function, for hardware
Note: this module is not working right now. The working Bayesian Firmware Searcher is in mappers/smapper.py
"""


class BayesianSearcher:

    def __init__(self):
        self.bayes_model = None  # Bayesian optimizer model used to conduct search
        self.param_point_set = None  # This is a big nested tuple point-set of N-vectors for N params
        self.param_bounds = OrderedDict()  # Map: label -> (min, max)
        self.param_labels = None  # String tuple of size N where each entry is the name of a param
        self.searcher = None  # Searcher wrapper, which has access to the MetaArch and Smapper Units (HW and FW)

    def init_searcher(self, meta_arch_path, nn_path):
        self.searcher = yaml_searcher_factory(meta_arch_path, nn_path)
        hw_params = tuple(self.searcher.meta_arch.argument_combs)
        hw_param_labels = self.searcher.meta_arch.param_set_labels
        # Now init the firmware operationalizer
        self.searcher.meta_arch.update_base_arch(hw_params[0])
        self.searcher.firmware_mapper.architecture = self.searcher.meta_arch.base_arch
        self.searcher.firmware_mapper.run_operationalizer(run_ops=False)
        fw_params = tuple(self.searcher.firmware_mapper.param_op_map.keys())
        fw_param_labels = self.searcher.firmware_mapper.param_labels
        hw_fw_combs = itertools.product(hw_params, fw_params)
        param_point_set = ((*hw, *fw) for hw, fw in hw_fw_combs)
        param_labels = (*hw_param_labels, *fw_param_labels)
        self.set_params(tuple(param_point_set), param_labels)

    def set_params(self, param_point_set: tuple, param_labels: tuple):
        """
        Sets the N parameters that we wish for the Bayesian model to optimize over. This includes both hardware
        and firmware parameters. Also calculates the parameter bounds
        :param param_point_set: Tuple set with each entry being an N-vector
        :param param_labels: string tuple of size N where each entry is the name of each parameter
        :return: None
        """
        self.param_point_set = param_point_set
        self.param_labels = param_labels
        # Calculate param_bounds, so iterate over N
        for i in range(len(self.param_labels)):
            dimension_i = [p[i] for p in param_point_set]
            max_i, m = max(dimension_i), min(dimension_i)
            min_i = m - 0.001 if max_i == m else m # This is to avoid the error when putting bounds in Bayes model
            self.param_bounds[self.param_labels[i]] = (min_i, max_i)

    def make_discrete_param(self, continuous_param_set: OrderedDict):
        """
        Turns a continuous parameter set suggested by the Bayesian Model into a discrete parameter set that
        is valid. For each value in the continuous param set
        :param continuous_param_set: The set of continuous params, size N
        :return: The parameter set made discrete, as an OrderedDict(). This will be put into **kwargs of Black Box Func
        """
        discrete_params = OrderedDict()
        for i in range(len(self.param_labels)):
            continous_value = tuple(continuous_param_set.values())[i]
            closest_discrete_val = sorted([(abs(p[i] - continous_value), p[i]) for p in self.param_point_set])[0][1]
            discrete_params[self.param_labels[i]] = closest_discrete_val
        return discrete_params

    def bayesian_trial(self, **kwargs):
        param_dict = OrderedDict(locals()['kwargs'])
        print(param_dict)
        # Since these are continuous variables, make discrete
        discrete_params = self.make_discrete_param(param_dict)
        print(discrete_params)
        # Create Architecture and Operations from this map_set
        hw_params = tuple([v for k, v in discrete_params.items() if k.startswith("hardware")][::-1])
        fw_params = tuple([v for k, v in discrete_params.items() if k.startswith("firmware")][::-1])
        print(hw_params, fw_params)
        self.searcher.meta_arch.update_base_arch(hw_params)
        architecture = self.searcher.meta_arch.base_arch
        operations = self.searcher.firmware_mapper.param_op_map[fw_params]
        estimator = Estimator(architecture, operations)
        energy, area, cycle = estimator.estimate(["energy", "area", "cycle"], analysis=False)
        score = self.score_function(energy, area, cycle)
        return score

    def score_function(self, energy, area, cycle):
        return -1 * energy * area * cycle

    def run_bayes_model(self):
        self.bayes_model = BayesianOptimization(f=self.bayesian_trial,
                                                pbounds=self.param_bounds,
                                                random_state=1,
                                                verbose=False)
        self.bayes_model.maximize(10, 10)
        print(self.bayes_model.max)