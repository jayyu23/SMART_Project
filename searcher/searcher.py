from searcher.meta_architecture import MetaArchitecture
from estimator.utils import read_yaml_file
from mappers.smapper.smapper import Smapper
from mappers.smapper.logger import Logger
from copy import deepcopy
import numpy, time
import matplotlib.pyplot as plt


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

    def search_combinations(self):
        # Outer loop: architecture
        top_solutions_num = 3
        start_time = time.time()
        for hw_param_set, architecture in self.meta_arch.iter_architectures():
            # Set the architecture for the firmware searcher
            self.logger.add_line("="*20)
            self.logger.add_line(f"Hardware param: {architecture.config_label}")
            self.firmware_mapper.architecture = architecture
            self.firmware_mapper.run_operationalizer()
            bayes_fw_input, score, eac = self.firmware_mapper.search_firmware(algorithm="bayes")
            search_space = len(self.firmware_mapper.param_op_map)
            self.logger.add_line(f"Firmware param (Best from Bayesian Opt): {bayes_fw_input}")
            self.logger.add_line(f"\t\tScore:{score}")
            self.logger.add_line(f"\t\tEnergy (pJ), Area (um^2), Cycle:{eac}")
            self.logger.add_line(f"Search space: {search_space} firmware possibilities")
            self.combinations_searched += search_space
            if len(self.top_solutions) < top_solutions_num:
                self.top_solutions.append([score, bayes_fw_input, eac, deepcopy(architecture)])
                self.top_solutions.sort()
            elif score < self.top_solutions[-1][0]:
                self.top_solutions[-1] = [score, bayes_fw_input, eac, deepcopy(architecture)]
            """
            # This script is intermediate, used to evaluate the effectiveness of bayes search against linear search
             N = 1 # Top N firmware choices for each hardware recorded
            self.firmware_mapper.search_firmware(algorithm="linear")
            self.firmware_mapper.print_rankings(N)

            num_fw_possibilities = len(self.firmware_mapper.top_solutions)
            # print(num_fw_possibilities)

            for rank in range(num_fw_possibilities):
                if self.firmware_mapper.top_solutions[rank][2] == bayes_fw_input:
                    percentile = round(100*(1 - (rank/num_fw_possibilities)), 2)
                    print(f"Bayesian solution is rank {rank + 1} out of {num_fw_possibilities}")
                    print(f"Better than {percentile}% of solutions")
                    self.bayes_percentile.append(percentile)
                    break
            solution_data = list((hw_param_set, fw_param_set, result) for score, result, fw_param_set
                                  in self.firmware_mapper.top_solutions[:N])
            self.combinations_searched += len(self.firmware_mapper.param_op_map)
            self.hw_fw_result += solution_data
            self.linear_bayes['linear'].append(self.firmware_mapper.top_solutions[0][0])
            self.linear_bayes['bayes'].append(score)
        """
        # Summarize the search
        end_time = time.time()
        self.logger.add_line("="*20)
        self.logger.add_line(f"Total: {self.combinations_searched} combinations searched")
        self.logger.add_line("="*20)
        self.logger.add_line(f"Top solutions found:")
        for solution_i in range(top_solutions_num):
            solution = self.top_solutions[solution_i]
            self.logger.add_line(f"***Rank {solution_i}***")
            self.logger.add_line(f"\t\tScore: {solution[0]}")
            self.logger.add_line(f"\t\tEnergy (pJ), Area (um^2), Cycle: {solution[2]}")
            self.logger.add_line(f"\t\tHardware: {solution[3].config_label}")
            self.logger.add_line(f"\t\tFirmware: {solution[1]}")
        self.logger.add_line(f"Execution time: {end_time - start_time} seconds")
        self.logger.write_out(f"project_io/test_run/search_log{time.time_ns()}.txt")

    def graph_results_3d(self):
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