# SMART Searcher

*Updated 2021-06-07 by Jay Yu*

*Shensilicon Semiconductors*

## Overview

The **Shensilicon Microchip Architectural Reference Tool (SMART)** is a project designed to provide assistance in the design of the Shensilicon TH-series microchips through quantitative analysis of architectures' **energy (pJ)**, **area (um^2)** and **cycle** consumption when running Neural Networks. 

The **SMART Searcher** is a hardware searcher that will search for optimal hardware architectures for a Neural Network within the constraints as defined in the `meta-architecture.yaml` template. It first lists out all of the different hardware architectures that are valid within the constraints, then uses the **SMART Smapper** to obtain an optimal firmware score for each hardware architecture. It then ranks the hardware architectures accordingly, and uses the **SMART Estimator** to output detailed analysis and breakdowns for the top hardware architectures identified.

- Inputs:

  - Meta-Architecture YAML: describing the range of hardware options to be searched
  - Neural Network YAML: describing the neural network to be mapped (currently supports DNN and CNN shapes)
  - Firmware Algorithm: `bayes` or `linear` algorithm to search firmware (defined in Smapper)
  - Hardware Algorithm: `bayes` or `linear` algorithm to search hardware
  - Verbose: `boolean` whether the output log should include data of all the architectures trialed

  

  Steps:

  1. `meta-architecture.py` first creates the different architecture combinations that are possible given the constraints in the `meta--architecture.yaml`

  2. For each Architecture, run the `neural_network.yaml` with the Architecture in the Smapper, to obtain the score and optimal firmware information.

  3. Rank the hardware architectures according to the scores of their optimal firmware. For the top N architectures, output detailed analysis and breakdown by running the SMART Estimator again.


  Outputs:

  - Search Log detailing the top hardware-firmware combinations found, and all of the different hardware architecture searched (if verbose)
  - Detailed analysis (described in the output of the Estimator) of the ranked top hardware-firmware

## Quick Start

In the main `SMART_Project` directory, execute `main.py` with no runtime arguments to run the Searcher module, which is a hardware searcher.

The Searcher module takes two inputs, defined in `main.py` code (`run_searcher()` method):

- Neural Network Shape: `project_io/searcher_input/neural_network.yaml`. Currently supports DNN and CNN model shapes.
- Meta-Architecture Model: `project_io/searcher_input/original_arch/meta_architecture.yaml`. The meta compound components used in this architecture are defined in the `meta_components` folder in the same directory

Searcher will output the results of the search in the folder of `project_io/test_run/run_{run_id}` where `run_id` is given by `time.time_ns()`

## Functionality

As of **SMART v1.0**, the SMART Searcher has the following capabilities:

- [x] Define Meta-Architecture YAML template, which is based on the Architecture YAML template but allows the user to use a list to define the different hardware parameters they wish to be searched along
- [x] Define Meta-Compound-Component YAML, which is based on the Compound Component YAML, but allows the user to use a list to define the different hardware parameters they wish to be searched along
- [x] Allow the user to define multiple instances of the same component inside the Meta-Compound-Component, and vary the amount of instances like a search parameter
- [x] Create a searching algorithm that can iterate over the different hardware architectures possible as constrained by the Meta-Architecture YAML, and connect this to the Smapper API
- [x] Add in a logger module to record the different hardware-firmware combinations searched, as well as keep track of how many combinations have been searched
- [x] Rank the different hardware architectures according to their best-performing firmware results.
- [x] For the top N architecture solutions (with N defined by the user), output the detailed analysis as a folder, consisting of pie charts, TXT analysis, and the relevant component-operation matrix.

## Sample Output

Partial selection of verbose output

```

░██████╗███╗░░░███╗░█████╗░██████╗░████████╗
██╔════╝████╗░████║██╔══██╗██╔══██╗╚══██╔══╝
╚█████╗░██╔████╔██║███████║██████╔╝░░░██║░░░
░╚═══██╗██║╚██╔╝██║██╔══██║██╔══██╗░░░██║░░░
██████╔╝██║░╚═╝░██║██║░░██║██║░░██║░░░██║░░░
╚═════╝░╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░
Shensilicon Microchip Architectural Reference Tool
==================================================
[2021-06-04 14:11:12]: ==================================================
[2021-06-04 14:11:12]: Hardware param: {'hardware_sgemm_sram_size': 256, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 1000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 512, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 8, 'hardware_mac_datasize': 8}
[2021-06-04 14:11:12]: Firmware param (Best from Bayesian Opt): {'firmware_in_w': 8, 'firmware_in_h': 110, 'firmware_out_h': 4}
[2021-06-04 14:11:12]: 		Score: 17.832593897943944
[2021-06-04 14:11:12]: 		Energy (pJ), Area (um^2), Cycle: (39560816.34048, 1157872.38, 14848)
[2021-06-04 14:11:12]: Search space: 366 firmware possibilities
[2021-06-04 14:11:13]: ==================================================
[2021-06-04 14:11:13]: Hardware param: {'hardware_sgemm_sram_size': 256, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 1000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 512, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 8, 'hardware_mac_datasize': 16}
[2021-06-04 14:11:13]: Firmware param (Best from Bayesian Opt): {'firmware_in_w': 8, 'firmware_in_h': 110, 'firmware_out_h': 4}
[2021-06-04 14:11:13]: 		Score: 17.55290833026434
[2021-06-04 14:11:13]: 		Energy (pJ), Area (um^2), Cycle: (38769417.17504, 1160960.38, 7936)
[2021-06-04 14:11:13]: Search space: 366 firmware possibilities
[2021-06-04 14:13:02]: ==================================================
[2021-06-04 14:13:02]: Hardware param: {'hardware_sgemm_sram_size': 32000, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 64000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 256000, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 16, 'hardware_mac_datasize': 16}
[2021-06-04 14:13:02]: Firmware param (Best from Bayesian Opt): {'firmware_in_w': 16, 'firmware_in_h': 220, 'firmware_out_h': 128}
[2021-06-04 14:13:02]: 		Score: 21.198529336096104
[2021-06-04 14:13:02]: 		Energy (pJ), Area (um^2), Cycle: (1988187498.00136, 225314784.38, 3526)
[2021-06-04 14:13:02]: Search space: 640 firmware possibilities
[2021-06-04 14:13:02]: ==================================================
[2021-06-04 14:13:02]: Total: 75284 combinations searched
[2021-06-04 14:13:02]: ==================================================
[2021-06-04 14:13:02]: Top solutions found:
[2021-06-04 14:13:02]: #1		********************
[2021-06-04 14:13:02]: 		Score: 17.2892960707294
[2021-06-04 14:13:02]: 		Energy (pJ), Area (um^2), Cycle: (38352641.192959994, 1166304.38, 4352)
[2021-06-04 14:13:02]: 		Hardware: {'hardware_sgemm_sram_size': 256, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 1000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 512, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 16, 'hardware_mac_datasize': 16}
[2021-06-04 14:13:02]: 		Firmware: {'firmware_in_w': 8, 'firmware_in_h': 110, 'firmware_out_h': 4}
[2021-06-04 14:13:02]: #2		********************
[2021-06-04 14:13:02]: 		Score: 17.503577690777128
[2021-06-04 14:13:02]: 		Energy (pJ), Area (um^2), Cycle: (44605955.24096, 1642464.38, 4352)
[2021-06-04 14:13:02]: 		Hardware: {'hardware_sgemm_sram_size': 1000, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 1000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 512, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 16, 'hardware_mac_datasize': 16}
[2021-06-04 14:13:02]: 		Firmware: {'firmware_in_w': 8, 'firmware_in_h': 110, 'firmware_out_h': 4}
[2021-06-04 14:13:02]: #3		********************
[2021-06-04 14:13:02]: 		Score: 17.552457589390148
[2021-06-04 14:13:02]: 		Energy (pJ), Area (um^2), Cycle: (38756975.57504, 1160128.38, 7936)
[2021-06-04 14:13:02]: 		Hardware: {'hardware_sgemm_sram_size': 256, 'hardware_sgemm_sram_width': 64, 'hardware_data_sram_size': 1000, 'hardware_data_sram_width': 64, 'hardware_his_sram_size': 64, 'hardware_his_sum_sram_size': 8, 'hardware_model_sram_size': 512, 'hardware_model_sram_width': 64, 'hardware_mac_instances': 16, 'hardware_mac_datasize': 8}
[2021-06-04 14:13:02]: 		Firmware: {'firmware_in_w': 8, 'firmware_in_h': 110, 'firmware_out_h': 4}
[2021-06-04 14:13:02]: Execution time: 109.86680126190186 seconds
```

