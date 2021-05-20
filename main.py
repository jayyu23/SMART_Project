from estimator.estimator import Estimator, estimator_factory
from mappers.smapper.smapper import Smapper
import time


def run_estimator():
    est = estimator_factory("project_io/mapper_output/architecture.yaml",
                    "project_io/mapper_output/operations.yaml",
                    components_folder="project_io/mapper_output/components/",
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
    print("Execution time: ", end_time - start_time, "seconds")


if __name__ == "__main__":
    run_smapper()
