from searcher.meta_architecture import MetaArchitecture
from estimator.utils import read_yaml_file
from mappers.smapper.smapper import Smapper
import numpy
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
        self.linear_bayes = {'linear': [], 'bayes': []}
        self.bayes_percentile = []

    def set_nn(self, nn_path):
        self.firmware_mapper.set_nn(nn_path)

    def set_meta_arch(self, meta_arch_path):
        self.meta_arch = MetaArchitecture(read_yaml_file(meta_arch_path))
        self.meta_arch.load_argument_combinations()

    def search_combinations(self):
        N = 1 # Top N firmware choices for each hardware recorded
        # Outer loop: architecture
        for hw_param_set, architecture in self.meta_arch.iter_architectures():
            # Set the architecture for the firmware searcher
            print()
            print("Searching param set",hw_param_set, architecture)
            self.firmware_mapper.architecture = architecture
            self.firmware_mapper.run_operationalizer()
            bayes_input, score = self.firmware_mapper.search_firmware(algorithm="bayes")
            self.firmware_mapper.search_firmware(algorithm="linear")
            self.firmware_mapper.print_rankings(N)

            num_fw_possibilities = len(self.firmware_mapper.top_solutions)
            print(num_fw_possibilities)

            for rank in range(num_fw_possibilities):
                if self.firmware_mapper.top_solutions[rank][2] == bayes_input:
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
        print()
        print("="*20)
        print(f"Total: {self.combinations_searched} combinations searched")


    def rank_results(self):
        # TODO: Ranking algorithm
        pass

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