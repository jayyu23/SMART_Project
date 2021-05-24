# Shensilicon Microchip Architectural Reference Tool

*Updated 2021-05-20 by Jay Yu*

*Shensilicon Semiconductors*

## Overview

The Shensilicon Microchip Architectural Reference Tool is a project designed to provide architecture-level feature estimations of Shensilicon TH-series microchips. The features included within the SMART project are **energy (pJ)**, **area (um^2)** and **cycle** data.

## Dependencies

The following packages are used outside of the default Python packages. These need to be installed via:

```bash
pip install -r requirements.txt
```

## Quick Start

### Smapper
In the main `SMART_Project` directory, execute `main.py` with no runtime arguments to run the Smapper module, which is a firmware searcher.

The Smapper module takes two inputs, defined in `main.py` code (`run_smapper()` method):
- Neural Network Shape: `project_io/mapper_input/neural_network.yaml`. Currently only supports DNN model shape
- Architecture Model: `project_io/mapper_input/architecture.yaml`. The compound components used in this architecture are defined in the `components` folder in the same directory

Smapper will output onto terminal results of firmware combinations estimated, and a ranking of the firmware.

### Estimator

To run only the SMART Estimator from an `architecture` file and `operations` file, change the `__main__` method in`main.py` to run estimator, and enter the architecture/operations file paths
Defaults:
- Architecture Model: `project_io/mapper_output/architecture.yaml` The compound components used in this architecture are defined in the `components` folder in the same directory
- Operations List: `project_io/mapper_output/operations.yaml`

## Project Timeline

The SMART project is split into three parts, as follows:

|      | Name               | Target   | Goals                                                        | Timeline          |
| ---- | ------------------ | -------- | ------------------------------------------------------------ | ----------------- |
| 1    | Architecture Phase | Hardware | Define and model hardware architectural components and corresponding operations. Output Feature Estimation documents | Feb 20 - March 20 |
| 2    | Mapping Phase      | Firmware | Define and model DNN shapes. Create "mappings" representing firmware that places DNN shape onto the hardware architecture | March 20 - May 1  |
| 3    | Searching Phase    | Software | Given a set of DNN parameters and constraints, automatically generate optimized mappings using a searching algorithm. | May 1 - June 15   |

## Functionality

### Part 1:  Architecture  Phase (Estimator)

As of 2021-04-06, SMART has completed the requirements for Part 1. It is able to:

- [x] Read and store "Primitive Components" (PC) -- which are basic hardware units such as registers, MAC units, SRAM --  in a SQLite database, the *Intelligent Primitive Component Library* (IPCL)

- [x] Within the IPCL, each database represents a different hardware configuration, and each PC has an accompanying set of "feature scripts" to calculate the features of **energy, area, cycle**.

- [x] Allow the user to instantiate "Compound Components," (CC) which are different combinations of PCs and other CCs, allowing for the description of components that have more than one individual component inside (eg. a Processing Element may contain both a MAC unit and a register)

- [x] Allow the user to define an Architecture YAML template using both PC and CC

- [x] Allow the user to define an Operations YAML template detailing the operations to be conducted, which easily describe serial/parallel actions as well as loops, providing support for loop nesting

- [x] Output Feature Reference Tables for the features of **energy, area, cycle**, given an Architecture template, detailing statistics for each component's operation.

- [x] Output Feature Estimation for the features of **energy, area, cycle**, given an Architecture and Operations template

- [x] Output Component Breakdowns for each Feature Estimation as a Pie Chart

- [x] Output the Component-Operation Matrix for each Feature Estimation as a .csv file

### Part 2: Mapping Phase (Assembler + Operation Maker)

As of 2021-05-20, SMART has completed the following requirements for Part 2. It is able to:

- [x] Given the binary descriptors (64 bit machine code), output relevant Assembly code through a disassembler

- [x] Given this machine code, create corresponding Operations for VAD and ASR

- [x] Create, from a set of parameters, operations and architecture templates as defined in Phase 1

- [x] Given a Neural Network shape, generate different firmware solutions for the network, and rank these firmware solutions

### Sample Output: VAD Cycle Estimation

```
░██████╗███╗░░░███╗░█████╗░██████╗░████████╗
██╔════╝████╗░████║██╔══██╗██╔══██╗╚══██╔══╝
╚█████╗░██╔████╔██║███████║██████╔╝░░░██║░░░
░╚═══██╗██║╚██╔╝██║██╔══██║██╔══██╗░░░██║░░░
██████╔╝██║░╚═╝░██║██║░░██║██║░░██║░░░██║░░░
╚═════╝░╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░
Shensilicon Microchip Architectural Reference Tool
==================================================
===== Cycle Estimation ======
	Component: psram
	Value: 0 cycles

	Component: npu_pe
	Value: 6752 cycles

	Component: global_status_reg
	Value: 30 cycles

	Component: npu_ctrl
	Value: 128 cycles

	Component: sgemm_sram
	Value: 65 cycles

	Component: data_sram
	Value: 179 cycles

	Component: his_sram
	Value: 252 cycles

	Component: his_sum_sram
	Value: 1536 cycles

	Component: model_sram
	Value: 5520 cycles

====================
Total Cycle Estimation: 7380 cycles
```
### Sample Output: Pie Chart for VAD Cycle Estimation

![Image](project_io/estimation_output/ref-output/vad_cycle_piechart.png)
