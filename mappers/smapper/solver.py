"""
The role of the Solver is to find potential partition solutions for a neural network with certain dimensions.
Breaks a big NN into many small NNs
"""
from mappers.smapper.wrappers import NeuralNetwork
import numpy


def factorize(num: int):
    out = []
    for i in range(1, int(num ** 0.5) + 1):
        if num % i == 0:
            out += [i, int(num / i)]
    return out


class Solver:
    def __init__(self, nn: NeuralNetwork):
        self.nn = nn
        self.factor_comb = None
        self.param_labels = None
        self.problem = None # Entire problem if it were one tile, i.e repeat = 1. Used to calculate repeat
        if self.nn.nn_type == "dnn":
            self.factor_comb = self.__dnn_solve()

    def __dnn_solve(self):
        # Finds the factors of the neural network dimensions
        self.param_labels = ["firmware_in_w", "firmware_in_h", "firmware_out_h"]
        dims = self.nn.dimensions
        in_w, in_h, out_h = dims["in_width"], dims['in_height'], dims['out_height']
        # Factorize the combinations
        fac1, fac2, fac3 = factorize(in_w), factorize(in_h), factorize(out_h)
        # Create factor combinations
        solve_combs = list([x, y, z] for x in fac1 for y in fac2 for z in fac3)
        self.problem = numpy.array((in_w, in_h, out_h))
        # for row in solve_combs:
        #    row.append(int((numpy.array((in_w, in_h, out_h)) / (numpy.array(row))).prod()))
        return solve_combs
