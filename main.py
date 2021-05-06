from estimator.estimator import Estimator

est = Estimator("project_io/mapper_output/architecture.yaml",
                "project_io/mapper_output/operations.yaml",
                components_folder="project_io/mapper_output/components/",
                db_table="TH2Components")

print(est.operation_list)
est.estimate(features=["cycle"])
