from estimator.estimator import Estimator, estimator_factory
from estimator.input_handler import database_handler
from estimator.data_structures.primitive_component import PrimitiveComponent
from mappers.smapper.smapper import Smapper
import time
from estimator.utils import read_yaml_file
from searcher.meta_architecture import MetaArchitecture


def run_estimator():
    est = estimator_factory("project_io/estimator__input/architecture.yaml",
                            "project_io/estimator__input/operations.yaml",
                            components_folder="project_io/estimator__input/components/",
                            db_table="TH2Components")

    print(est.operation_list)
    est.estimate(features=["cycle"])


def run_smapper():
    sm = Smapper()
    sm.set_architecture("project_io/mapper_input/architecture.yaml",
                        components_folder="project_io/mapper_input/components/",
                        database_table="TH2Components")
    sm.set_nn("project_io/mapper_input/neural_network.yaml")
    start_time = time.time()
    sm.run_operationalizer()
    sm.graph_energy_cycle()
    sm.print_top_solutions()
    end_time = time.time()
    # print(sm.get_operations_from_param((16, 440, 128, 1))) # Get operation set for this param
    print("Execution time: ", end_time - start_time, "seconds")


def run_arch_finder():
    database_handler.set_ipcl_table("TH2Components")
    meta_arch = read_yaml_file("project_io/searcher_input/meta_architecture.yaml")
    start_time = time.time()
    ma = MetaArchitecture(meta_arch)
    ma.get_argument_combinations()
    for c in ma.iter_architectures():
        print(c)
    end_time = time.time()
    print("Execution time: ", end_time - start_time, "seconds")


if __name__ == "__main__":
    run_arch_finder()
