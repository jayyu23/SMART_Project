"""
The role of the Solver is to find potential partition solutions for a neural network with certain dimensions.
Breaks a big NN into many small NNs
"""
from collections import OrderedDict

from mappers.smapper.wrappers import NeuralNetwork
import numpy
import itertools


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
        self.original_tile = None # Original tile
        self.__solve_maps = {'dnn': self.__dnn_solve, 'cnn': self.__cnn_solve}
        self.factor_comb = self.__solve_maps[self.nn.nn_type]()

    def __dnn_solve(self):
        """
        Find tiling solutions for a DNN
        :return: Tiling combinations for a DNN
        """
        # Finds the factors of the neural network dimensions
        self.param_labels = ["firmware_in_w", "firmware_in_h", "firmware_out_h"]
        dims = self.nn.dimensions
        in_w, in_h, out_h = dims["in_width"], dims['in_height'], dims['out_height']
        # Tile along all 3 dimensions
        fac1, fac2, fac3 = factorize(in_w), factorize(in_h), factorize(out_h)
        # Create factor combinations
        solve_combs = list([x, y, z] for x in fac1 for y in fac2 for z in fac3)
        self.original_tile = numpy.array((in_w, in_h, out_h))
        return solve_combs

    def __cnn_solve(self):
        """
        Tiling possibilities for a CNN, along the psum_h and psum_w dimensions.
        Not considering permutations of access with regards to data exploitation
        :return: Tiling combinations for CNN
        """
        dims = self.nn.dimensions
        fmap_height, kernel_height = dims['fmap_height'], dims['kernel_height']
        fmap_width, kernel_width = dims['fmap_width'], dims['kernel_width']
        psum_height = fmap_height - kernel_height + 1
        psum_width = fmap_width - kernel_width + 1
        # Tile along psum_height and psum_width dimensions. This determines the input size that needs to be read.
        self.param_labels = ["firmware_psum_height", "firmware_psum_width"]
        self.original_tile = (psum_height, psum_width)
        out_tile_height_width = tuple(itertools.product(factorize(psum_height), factorize(psum_width)))
        return out_tile_height_width
