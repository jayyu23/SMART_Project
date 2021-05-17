from estimator.estimator import Estimator
from mappers.smapper.smapper import Smapper
from mappers.smapper.solver import Solver
from mappers.smapper.wrappers import write_yaml, NeuralNetwork


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
    sm.run_operationalizer()



def run_solver():
    sm = Smapper()
    sm.set_nn("project_io/mapper_input/neural_network.yaml")
    n = sm.nn_list[0]
    nn = NeuralNetwork(n['name'], n['nn_type'], n['dimensions'], n['start'], n['end'])
    solver = Solver(nn)
    solutions = solver.solve()
    print(len(solutions))


if __name__ == "__main__":
    run_smapper()
