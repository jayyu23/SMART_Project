from estimator.estimator import Estimator
from searcher.meta_architecture import MetaArchitecture
from estimator.utils import read_yaml_file
from mappers.smapper.smapper import Smapper
from searcher.logger import Logger
from copy import deepcopy
import time
import os


def yaml_searcher_factory(meta_arch_path, meta_cc_path, nn_path):
    """
    Initializes a Searcher object according to the parameters specified
    :param meta_arch_path: Path to the meta-architecture YAML file
    :param meta_cc_path: Path to the meta-compound-components folder
    :param nn_path: Path to the Neural Network YAML file
    :return: Searcher object
    """
    s = Searcher()
    s.set_nn(nn_path)
    s.set_meta_arch(meta_arch_path, meta_cc_path)
    return s


class Searcher:
    """
    SMART Searcher is a hardware searcher that will search for hardware architectures given a neural network and a
    set of architecture constraints.
    """
    def __init__(self):
        self.meta_arch = None
        self.firmware_mapper = Smapper()
        self.hw_fw_result = list()
        self.combinations_searched = 0
        self.bayes_percentile = []
        self.logger = Logger()
        self.top_solutions = []

    def set_nn(self, nn_path):
        """
        Sets the neural network as defined in a Neural Network YAML file.
        Currently supports descriptions for DNN and CNN
        :param nn_path: Path to the Neural Network YAML file
        :return: None
        """
        self.firmware_mapper.set_nn(nn_path)

    def set_meta_arch(self, meta_arch_path, meta_cc_path):
        """
        Sets the meta-architecture to be searched. A meta-architecture describes the constraints of the architecture
        and the range of different possibilities to be searched. A Meta-Compound-Component similarly describes the
        possibility space where SMART should search for valid architectures
        :param meta_arch_path: Path to the meta-architecture YAML file
        :param meta_cc_path: Path to the meta-compound-component directory
        :return: None
        """
        self.meta_arch = MetaArchitecture(read_yaml_file(meta_arch_path), meta_cc_path)
        self.meta_arch.load_argument_combinations()

    def search_combinations(self, top_solutions_num=3, algorithm="bayes", verbose=False):
        """
        Key algorithm to (1) search for different hardware-firmware combinations, (2) rank all these HW-FW combinations,
        and (3) output detailed component analysis for the top N architectures
        :param top_solutions_num: Number of top solutions to be analyzed in detail
        :param algorithm: Algorithm used to search for firmware. Currently supports Bayesian Optimization ('bayes'),
        which is default, and linear-exhaustive search ('linear')
        :param verbose: Whether the output log should include details of all the different hardware-firmware
        combinations searched
        :return: None. Will output search results in test_run folder, keeping track of search log details etc.
        """
        start_time = time.time()
        algorithm_names = {'bayes': 'Bayesian Opt', 'linear': 'linear search'}
        # Outer loop: hardware architecture search
        for architecture in self.meta_arch.iter_architectures():
            # Inner loop: firmware operations search
            self.firmware_mapper.architecture = architecture
            self.firmware_mapper.run_operationalizer()
            # Firmware operations search, using Bayesian Optimization algorithm
            fw_input, score, eac = self.firmware_mapper.search_firmware(algorithm=algorithm)
            search_space = len(self.firmware_mapper.param_op_map)
            if verbose:
                self.logger.add_line("=" * 50)
                self.logger.add_line(f"Hardware param: {architecture.config_label}")
                self.logger.add_line(f"Firmware param (Best from {algorithm_names[algorithm]}): {fw_input}")
                self.logger.add_line(f"\t\tScore: {score}")
                self.logger.add_line(f"\t\tEnergy (pJ), Area (um^2), Cycle: {eac}")
                self.logger.add_line(f"Search space: {search_space} firmware possibilities")
            self.combinations_searched += search_space
            if len(self.top_solutions) < top_solutions_num:
                self.top_solutions.append([score, fw_input, eac, deepcopy(architecture)])
                self.top_solutions.sort(key=lambda x: x[0])
            elif score < self.top_solutions[-1][0]:
                self.top_solutions[-1] = [score, fw_input, eac, deepcopy(architecture)]
                self.top_solutions.sort(key=lambda x: x[0])
                # print("sorted", self.top_solutions)
        end_time = time.time()
        # Summarize the search, create output directory
        run_id = time.time_ns()
        out_dir = f"project_io/test_run/run_{run_id}"
        os.mkdir(out_dir)
        self.logger.add_line("="*50)
        self.logger.add_line(f"Total: {self.combinations_searched} combinations searched")
        self.logger.add_line("="*50)
        self.logger.add_line(f"Top solutions found:")
        for solution_i in range(top_solutions_num):
            solution = self.top_solutions[solution_i]
            self.logger.add_line(f"#{solution_i + 1}\t\t{'*'*20}")
            self.logger.add_line(f"\t\tScore: {solution[0]}")
            self.logger.add_line(f"\t\tEnergy (pJ), Area (um^2), Cycle: {solution[2]}")
            self.logger.add_line(f"\t\tHardware: {solution[3].config_label}")
            self.logger.add_line(f"\t\tFirmware: {solution[1]}")
        self.logger.add_line(f"Execution time: {end_time - start_time} seconds")
        self.logger.write_out(os.path.join(out_dir, "search_log.txt"))
        # Retrieve the optimal architecture + operations, and analyze in detail. (Pie charts)
        #   Do this by running Estimator again with analysis = True
        for i in range(top_solutions_num):
            solution_folder = os.path.join(out_dir, f"rank{i + 1}")
            os.mkdir(os.path.join(out_dir, f"rank{i + 1}"))
            analysis_arch = self.top_solutions[i][3]
            # Reset the firmware mapper to the winning architecture model
            self.firmware_mapper.architecture = analysis_arch
            self.firmware_mapper.run_operationalizer()  # To get the param_op map
            firmware_config = self.top_solutions[i][1]
            # print(firmware_config, self.firmware_mapper.fw_param_labels)
            param_op = tuple(firmware_config[x] for x in self.firmware_mapper.fw_param_labels)
            analysis_op = self.firmware_mapper.param_op_map[param_op]
            analysis_estimator = Estimator(analysis_arch, analysis_op)
            analysis_estimator.estimate(["energy", "area", "cycle"], analysis=True, out_dir=solution_folder)
