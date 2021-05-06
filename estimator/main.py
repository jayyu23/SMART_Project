from data_structures.compound_component import load_compound_components, compound_component_library
from data_structures.architecture import Architecture, flatten_operations
from input_handler import YAMLHandler, database_handler


# Testing scripts are functions called at runtime

def test_architecture_energy_estimation(arch_path="", op_path=""):
    yaml_handler_arch = arch_path if arch_path else "test/input/architecture_simple.yaml"
    yaml_handler_ops = op_path if op_path else "test/input/operations_seq.yaml"
    arch = YAMLHandler(yaml_handler_arch).get_as_dict()
    ops = YAMLHandler(yaml_handler_ops).get_as_dict()

    # Create an Architecture object
    my_arch = Architecture(arch)
    my_arch.set_operations(ops)
    for feature in ['energy', 'cycle', 'area']:
        print("Testing feature", feature)
        my_arch.print_current_reference_table(feature, False)
        my_arch.print_feature_estimation(feature)


def test_th2_primitive_energy_estimation():
    root_folder = "test/input/th2_npu_20210312/"
    yaml_handler_arch = root_folder + "architecture_th2.yaml"
    yaml_handler_ops = root_folder + "operations_th2.yaml"
    database_handler.set_ipcl_table("TH2Components")
    load_compound_components(root_folder + "components/")
    test_architecture_energy_estimation(yaml_handler_arch, yaml_handler_ops)


def test_th2_p2_energy_estimation():
    root_folder = "test/input/phase2_test/"
    yaml_handler_arch = root_folder + "architecture.yaml"
    yaml_handler_ops = root_folder + "operations.yaml"
    database_handler.set_ipcl_table("TH2Components")
    load_compound_components(root_folder + "components/")
    test_architecture_energy_estimation(yaml_handler_arch, yaml_handler_ops)


def test_simple_compound_components():
    load_compound_components()
    print("=" * 30)
    for n, c in compound_component_library.items():
        print(n, c.subcomponents)
    test_architecture_energy_estimation()


if __name__ == "__main__":
    test_th2_p2_energy_estimation()
