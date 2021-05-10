class NeuralNetwork:

    def __init__(self, type, dimensions, start, end):
        """
        Wrapper to describe a neural network
        :param type: Type of network (eg. DNN)
        :param dimensions: Dimension values of the NN, eg. in/out dim for DNN
        :param start: Components where the input starting information is held
        :param end: Components where the output information should be plaCED
        """
        self.type = type
        self.dimensions = dimensions
        self.start = start
        self.end = end


