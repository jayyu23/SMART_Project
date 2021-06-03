from estimator.estimator import Estimator
from searcher.meta_architecture import MetaArchitecture
from estimator.utils import read_yaml_file
from mappers.smapper.smapper import Smapper
from mappers.smapper.logger import Logger
from copy import deepcopy
import numpy, time
import matplotlib.pyplot as plt
import os


def yaml_searcher_factory(meta_arch_path, nn_path):
    s = Searcher()
    s.set_nn(nn_path)
    s.set_meta_arch(meta_arch_path)
    return s


class Searcher:
    def __init__(self):
        self.meta_arch = None
        self.firmware_mapper = Smapper()
        self.hw_fw_result = list()
        self.combinations_searched = 0
        self.bayes_percentile = []
        self.logger = Logger()
        self.top_solutions = []
        # self.linear_bayes = {'linear': [], 'bayes': []}

    def set_nn(self, nn_path):
        self.firmware_mapper.set_nn(nn_path)

    def set_meta_arch(self, meta_arch_path):
        self.meta_arch = MetaArchitecture(read_yaml_file(meta_arch_path))
        self.meta_arch.load_argument_combinations()

    def search_combinations(self, top_solutions_num=3, verbose=False):
        # Outer loop: hardware architecture search
        start_time = time.time()
        for hw_param_set, architecture in self.meta_arch.iter_architectures():
            # Inner loop: firmware operations search
            self.firmware_mapper.architecture = architecture
            self.firmware_mapper.run_operationalizer()
            # Firmware operations search, using Bayesian Optimization algorithm
            bayes_fw_input, score, eac = self.firmware_mapper.search_firmware(algorithm="bayes")
            search_space = len(self.firmware_mapper.param_op_map)
            if verbose:
                self.logger.add_line("=" * 50)
                self.logger.add_line(f"Hardware param: {architecture.config_label}")
                self.logger.add_line(f"Firmware param (Best from Bayesian Opt): {bayes_fw_input}")
                self.logger.add_line(f"\t\tScore: {score}")
                self.logger.add_line(f"\t\tEnergy (pJ), Area (um^2), Cycle: {eac}")
                self.logger.add_line(f"Search space: {search_space} firmware possibilities")
            self.combinations_searched += search_space
            if len(self.top_solutions) < top_solutions_num:
                self.top_solutions.append([score, bayes_fw_input, eac, deepcopy(architecture)])
                self.top_solutions.sort(key=lambda x: x[0])
            elif score < self.top_solutions[-1][0]:
                self.top_solutions[-1] = [score, bayes_fw_input, eac, deepcopy(architecture)]
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
        print([c[0] for c in self.top_solutions])
        for i in range(top_solutions_num):
            print(self.top_solutions[i][3].component_dict['npu_pe'].subcomponents)
            solution_folder = os.path.join(out_dir, f"rank{i + 1}")
            os.mkdir(os.path.join(out_dir, f"rank{i + 1}"))
            analysis_arch = self.top_solutions[i][3]
            # Reset the firmware mapper to the winning architecture model
            self.firmware_mapper.architecture = analysis_arch
            self.firmware_mapper.run_operationalizer()  # To get the param_op map
            firmware_config = self.top_solutions[i][1]
            param_op = tuple(firmware_config[x] for x in self.firmware_mapper.fw_param_labels)
            analysis_op = self.firmware_mapper.param_op_map[param_op]
            analysis_estimator = Estimator(analysis_arch, analysis_op)
            analysis_estimator.estimate(["energy", "area", "cycle"], analysis=True, out_dir=solution_folder)

    def graph_results_3d(self):
        # Legacy analytical code
        ax = plt.axes(projection='3d')
        x = numpy.log10(numpy.array([data[2][0] for data in self.hw_fw_result]))
        y = numpy.log10(numpy.array([data[2][1] for data in self.hw_fw_result]))
        z = numpy.log10(numpy.array([data[2][2] for data in self.hw_fw_result]))

        ax.scatter(x, y, z)
        ax.set_xlabel('energy log10')
        ax.set_ylabel('area log10')
        ax.set_zlabel('cycle log10')
        ax.set_title('Different Hardware-Firmware Combinations Costs')
        plt.show()

    def graph_results_2d(self):
        # Legacy analytical code
        ax = plt.axes()
        x = numpy.log10(numpy.array([data[2][1] for data in self.hw_fw_result]))
        y = numpy.log10(numpy.array([data[2][2] for data in self.hw_fw_result]))

        ax.scatter(x, y)
        for data in self.hw_fw_result:
            if data[0] == (32000, 64, 64000, 64, 64, 8, 256000, 64): # TH hardware
                color = "red"
                if data[1] == (16, 440, 128, 1):
                    color = "orange"
                x = numpy.log10(data[2][1])
                y = numpy.log10(data[2][2])
                ax.scatter(x, y, color=color)
        ax.set_xlabel('area log10')
        ax.set_ylabel('cycle log10')
        ax.set_title('Different Hardware-Firmware Combinations Costs')
        plt.show()

    def graph_linear_bayes(self):
        # Legacy Analytical Code
        """
        ax = plt.axes()
        x = numpy.log10(numpy.array([data[2][2] for data in self.hw_fw_result]))
        y1 = numpy.log10(numpy.array(self.linear_bayes['linear']))
        y2 = numpy.log10(numpy.array(self.linear_bayes['bayes']))
        ax.scatter(x, y1, color="blue")
        ax.scatter(x, y2, color="orange")
        ax.set_xlabel('area log10')
        ax.set_ylabel('cycles log10')
        ax.set_title('Bayes Searcher (orange) vs. Linear Searcher Results (blue)')
        plt.show()
        """
        ax = plt.axes()
        plt.hist(self.bayes_percentile)
        ax.set_title('Percentile Rank of Bayes Solution')
        plt.show()