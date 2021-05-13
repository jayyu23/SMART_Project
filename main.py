from estimator.estimator import Estimator
from mappers.smapper.smapper_main import Smapper
from mappers.smapper.wrappers import write_yaml

def run_estimator():
    est = Estimator("project_io/mapper_output/architecture.yaml",
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
    result, data = sm.map_nn()
    if result:
        write_yaml(data, "project_io/mapper_output/operations.yaml")


if __name__ == "__main__":
    run_smapper()
