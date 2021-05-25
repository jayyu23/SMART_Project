from estimator.estimator import Estimator, estimator_factory
from estimator.input_handler import database_handler
from estimator.data_structures.primitive_component import PrimitiveComponent
from mappers.smapper.smapper import Smapper
import time
from estimator.utils import read_yaml_file
from searcher.meta_architecture import MetaArchitecture
from searcher.searcher import Searcher, yaml_searcher_factory
from searcher.bayesian_searcher import BayesianSearcher


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
    sm.search_firmware()
    # sm.graph_energy_cycle()
    sm.rank_solutions()
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
    search = yaml_searcher_factory("project_io/searcher_input/meta_architecture.yaml",
                                   "project_io/mapper_input/neural_network.yaml")
    search.search_combinations()
    # search.graph_results_2d()
    print("Execution time: ", time.time() - start_time, "seconds")


def run_bayesian_searcher():
    bayes_searcher = BayesianSearcher()
    bayes_searcher.init_searcher("project_io/searcher_input/meta_architecture.yaml",
                                 "project_io/mapper_input/neural_network.yaml"
                                 )
    bayes_searcher.run_bayes_model()


if __name__ == "__main__":
    run_searcher()