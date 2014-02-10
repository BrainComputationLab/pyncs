import requests


class Normal(object):
    """ Class for a normal distribution of a parameter """

    def __init__(self, mean, stdev):
        self.mean = mean
        self.stdev = stdev


class Uniform(object):
    """ Class for a uniform distribution of a parameter """

    def __init__(self, min, max):
        self.min = min
        self.max = max


class Neuron(object):

    LIF_TYPE = "LIF_TYPE"
    IZH_TYPE = "IZH_TYPE"

    def __init__(self, neuron_type):
        self.neuron_type = neuron_type
