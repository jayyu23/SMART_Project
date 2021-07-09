from estimator.data_structures.architecture import yaml_arch_factory
from estimator.estimator import Estimator, estimator_factory
from estimator.input_handler import database_handler
from estimator.data_structures.primitive_component import PrimitiveComponent
from mappers.smapper.smapper import Smapper
import time
from estimator.utils import read_yaml_file
from searcher.meta_architecture import MetaArchitecture
from searcher.searcher import yaml_searcher_factory
from mappers.compiler.compiler import Compiler


def run_estimator():
    est = estimator_factory("project_io/estimator_input/sample_architecture.yaml",
                            "project_io/estimator_input/operations2.yaml",
                            components_folder="project_io/estimator_input/components/",
                            db_table="TH2Components")

    print(est.operation_list)
    est.estimate(features=["cycle", "energy", "area"], analysis=True)


def run_smapper():
    sm = Smapper()
    sm.set_architecture("project_io/mapper_input/architecture.yaml",
                        components_folder="project_io/mapper_input/components/",
                        database_table="TH2Components")
    sm.set_nn("project_io/mapper_input/neural_network.yaml")
    start_time = time.time()
    sm.run_operationalizer()
    sm.search_firmware()
    sm.graph_energy_cycle()
    # sm.print_rankings() # Legacy code
    end_time = time.time()
    # print(sm.get_operations_from_param((16, 440, 128, 1))) # Get operation set for this param
    print("Execution time: ", end_time - start_time, "seconds")


def run_arch_finder():
    database_handler.set_ipcl_table("TH2Components")
    meta_arch = read_yaml_file("project_io/searcher_input/meta_architecture.yaml")
    start_time = time.time()
    ma = MetaArchitecture(meta_arch)
    ma.load_argument_combinations()
    counter = 0
    for c in ma.iter_architectures():
        print(c)
        counter += 1
    end_time = time.time()
    print(f"Architectures searched: {counter} possibilities")
    print("Execution time: ", end_time - start_time, "seconds")


def run_searcher():
    start_time = time.time()
    search = yaml_searcher_factory("project_io/searcher_input/original_arch/meta_architecture.yaml",
                                   "project_io/searcher_input/original_arch/meta_components",
                                   "project_io/searcher_input/neural_network.yaml")
    search.search_combinations()
    print("Execution time: ", time.time() - start_time, "seconds")


def run_compiler():
    comp = Compiler(read_yaml_file("mappers/compiler/compiler_io/neural_network.yaml"),
                              yaml_arch_factory(read_yaml_file('project_io/estimator_input/architecture.yaml')))
    comp.compile()
    comp.write_out("mappers/compiler/compiler_io/pure_compiled_descriptor.txt", comment=False)
    comp.write_out("mappers/compiler/compiler_io/comment_compiled_descriptor.txt", comment=True)


if __name__ == "__main__":
    run_compiler()
