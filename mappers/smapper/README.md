# SMART Smapper

*Updated 2021-06-07 by Jay Yu*

*Shensilicon Semiconductors*



## Overview

The **Shensilicon Microchip Architectural Reference Tool (SMART)** is a project designed to provide assistance in the design of the Shensilicon TH-series microchips through quantitative analysis of architectures' **energy (pJ)**, **area (um^2)** and **cycle** consumption when running Neural Networks. 

The **SMART Smapper** (Solution Mapper) is the default module for firmware searching, and will find optimal mapping solutions for neural network on a given hardware architecture. The Smapper first searches for a range of possible firmware solutions and corresponding `operations.yaml` (as defined in the SMART Estimator), then uses the SMART Estimator to evaluate this `operations.yaml` on the given `architecture.yaml` 

Inputs:

- Architecture YAML file: describing the hardware architecture to be analyzed
- Neural Network YAML: describing the neural network to be mapped (currently supports DNN and CNN shapes)
- Search Algorithm: describing what algorithm to use to search for optimal mappings. Currently supports `linear`, which is an exhaustive linear search, and `bayes`, which is an adapted Bayesian-Optimization search algorithm. `bayes` is the default search algorithm, and highly recommended in cases of limited time and compute power. `linear` search is recommended only if there is sufficient compute and time available, and the absolute best firmware is needed.

Steps:

1. `solver.py`: Given the Neural Network, apply a factorization-based algorithm to find potential different tile sizes can 'solve' the problem

2. `operationalizer.py`: For each tile 'solution' given by the `solver`, check if it is valid on the Architecture given. If it is valid, create the corresponding `operations.yaml` that would  represent this 'solution'. 

3. `smapper.py` : For each firmware 'operations' identified above, run the SMART Estimator with the Architecture and corresponding Operations, retrieving energy, area, cycle data

4. `score_firmware(energy, area, cycle)`: Given the energy, area, cycle data, apply a 'scoring' function, which will output a single numeric score. The higher this score, the better the architecture (the search algorithm will find the `max` of the different scores). This function itself can be altered to accommodate specific situations. The default score function is:

   ```python
   return -1 * (math.log10(energy) + math.log10(area) + math.log10(cycle))
   ```

   *Note: We multiply by `-1` because a **lower** energy/area/cycle means a better architecture-operations combination, but our Bayesian-Optimization search algorithm can only search for **highest** scores, therefore need to adjust the score function accordingly*

Outputs:

- Optimal firmware mappings with the highest score, as searched through by the `algorithm` defined



## Quick Start

To run *only* the SMART Estimator on a specific `architecture.yaml` and `neural_network.yaml`

1. Make sure the packages in `dependencies.txt` are downloaded successfully
2. Change the function inside `main.py` to `run_smapper` and edit the file paths for the inputs



## Functionality

As of **SMART v1.0**, the SMART Smapper has the following capabilities:

- [x] Define the Neural Network YAML structure, so that it is able to describe the key features of a DNN/CNN
- [x] Given a Neural Network (DNN/CNN) shape, generate different tiling solutions based on factorization properties
- [x] Given a tiling combination, determine whether it can fit on a hardware Architecture. If so, generate the corresponding `operations.yaml` file, and connect this to the Estimator API
- [x] Define a scoring algorithm for firmware that takes in energy, area, cycle data, and outputs a weighted score. Rank the different firmware tiles according to the score they receive.
- [x] Use multiple firmware searching algorithms, including linear search and Bayesian Optimization method to conduct the firmware search, and allow the user to specify which algorithm to conduct firmware search





## Search Algorithms Note

As summarized above, `bayes` is the default search algorithm, and highly recommended in cases of limited time and compute power. `linear` search is recommended only if there is sufficient compute and time available, and the absolute best firmware is needed. *There is a tradeoff between search quality and search time required when using the Smapper*, and the user must keep this in mind, depending on its application. 

The Bayesian Optimization search algorithm is  based on the `fmfn/BayesianOptimization` package (MIT license), which uses a Gaussian Process Regressor. Because it does not exhaustively iterate over the search space, *it can only give a prediction/educated guess at the max value, and cannot guarantee that the firmware selected is the absolute best.* However, it requires significantly less time and compute power compared to linear-exhaustive search, and the overwhelming majority of its predictions are at least within the top 10% of firmware solutions searched using linear search (see histogram). 

 <img src="README-bayes-histogram.png" alt="README-bayes-histogram" style="zoom:100%;" />

Below are the summarized pros and cons of Bayesian Optimization and Linear Search:



|                       | Pros                                                         | Cons                                                         |
| --------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Bayesian Optimization | - Fast to run<br />- Solution in top 10%                     | - Cannot guarantee top 1 solution<br />- Top 10% result may still be far less effective than top 1 solution |
| Linear Search         | - Guarantees the absolute top solution<br /> - Can give a complete ranking of all of the results | - Very slow to run, requires significant time and compute    |

