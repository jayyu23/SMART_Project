class NeuralNetwork:

    def __init__(self, name, nn_type, dimensions, start, end):
        """
        Wrapper to describe a neural network
        :param name: Name of the network
        :param nn_type: Type of network (eg. DNN)
        :param dimensions: Dimension values of the NN, eg. in/out dim for DNN
        :param start: Components where the input starting information is held
        :param end: Components where the output information should be plaCED
        """
        self.name = name
        self.nn_type = nn_type
        self.dimensions = dimensions
        self.start = start
        self.end = end


