from searcher.meta_architecture import MetaArchitecture
from estimator.utils import read_yaml_file
from mappers.smapper.smapper import Smapper


def yaml_searcher_factory(meta_arch_path, nn_path):
    s = Searcher()
    s.set_nn(nn_path)
    s.set_meta_arch(meta_arch_path)
    return s


class Searcher:
    def __init__(self):
        self.meta_arch = None
        self.firmware_mapper = Smapper()

    def set_nn(self, nn_path):
        self.firmware_mapper.set_nn(nn_path)

    def set_meta_arch(self, meta_arch_path):
        self.meta_arch = MetaArchitecture(read_yaml_file(meta_arch_path))
        self.meta_arch.load_argument_combinations()

    def search_combinations(self):
        # Outer loop: architecture
        for hw_param_set, architecture in self.meta_arch.iter_architectures():
            # Set the architecture for the firmware searcher
            print()
            print("Searching param set",hw_param_set, architecture)
            self.firmware_mapper.architecture = architecture
            self.firmware_mapper.run_operationalizer()
            self.firmware_mapper.print_top_solutions(3)
