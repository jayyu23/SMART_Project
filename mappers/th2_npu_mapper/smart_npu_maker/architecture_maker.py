"""
Creates the TH NPU Architecture and compound components
Helps to integrate TH NPU specifications
"""
from smart_npu_maker.utils import *


class ArchitectureMaker:

    def __init__(self, mac_number=8, out_folder="smart_npu_maker/output/", name="TH_2608_NPU", version=0.4):
        self.out_folder = out_folder
        self.name = name
        self.version = version
        self.mac_number = mac_number

        self.compound_components, self.cc_instance_order = self.make_compound_components()
        self.arch_dict = self.make_npu_arch()

    def make_compound_components(self, instance_order: list = None):
        # 1. Make the PE
        out_dict = OrderedDict({"name": "processing_element",
                                "subcomponents": list(),
                                "operations": list()})
        # Add in MAC units, mac_number of them
        out_dict['subcomponents'] = [OrderedDict({"name": "mac_%s" % n,
                                                  "class": "intmac",
                                                  "arguments": {"datasize": 8}}) for n in range(self.mac_number)]
        # Add in SGEMM
        sgemm_op_dict = OrderedDict({"name": "mac", "definition":
            [OrderedDict({"type": "parallel", "operations": ["mac_%s.mac()" % n for n in range(self.mac_number)]})]})
        out_dict['operations'].append(sgemm_op_dict)
        # 2. Make the instance order
        out_instance_order = instance_order if instance_order else ["pe.yaml"]
        # Output
        write_yaml(OrderedDict({"compound_component": out_dict}), self.out_folder + "components/pe.yaml")
        write_yaml(out_instance_order, self.out_folder + "components/_instance_order.yaml")
        return out_dict, out_instance_order

    def make_npu_arch(self):
        out_dict = OrderedDict({"architecture": OrderedDict({"name": self.name, "version": self.version,
                                                             "components": []})})
        npu_group = OrderedDict({"type": "group", "name": "NPU", "components": []})
        comp_name_class_arg = (("npu_pe", "processing_element", None),
                               ("global_status_reg", "register", None),
                               ("npu_ctrl", "bitwise", None),
                               ("sgemm_sram", "sram", (("KBsize", 32),)),
                               ("data_sram", "sram", (("KBsize", 64),)),
                               ("his_sram", "sram", (("KBsize", 64),)),
                               ("his_sum_sram", "sram", (("KBsize", 8),)),
                               ("model_sram", "sram", (("KBsize", 256),)))

        npu_group['components'] = [component_arch_dict(x, y, z) for x, y, z in comp_name_class_arg]
        out_dict['architecture']['components'].append(component_arch_dict('psram', 'psram'))
        out_dict['architecture']['components'].append(npu_group)
        write_yaml(out_dict, self.out_folder + "architecture.yaml")
        return out_dict
