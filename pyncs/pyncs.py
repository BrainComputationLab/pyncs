import requests


class Simulator(object):

    STATUS_RUNNING = "STATUS_RUNNING"
    STATUS_IDLE = "STATUS_IDLE"

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_status():
        # TODO make this work
        return Simulator.STATUS_IDLE

    def run(simulation):
        pass


class Simulation(object):

    def __init__(self, model):
        self.model = model


class Entity(object):

    def to_dict():
        pass


class Normal(Entity):
    """ Class for a normal distribution of a parameter """

    def __init__(self, mean, stdev):
        self.mean = mean
        self.stdev = stdev


class Uniform(Entity):
    """ Class for a uniform distribution of a parameter """

    def __init__(self, min, max):
        self.min = min
        self.max = max


class Neuron(Entity):
    """ Class for the neuron entity """

    def __init__(self, neuron_type):
        self.neuron_type = neuron_type


class Channel(Entity):

    LIF_VOLTAGE_GATED = "LIF_VOLTAGE_GATED"
    LIF_CALCIUM_DEPENDENT = "LIF_CALCIUM_DEPENDENT"
    HH_VOLTAGE_GATED = "HH_VOLTAGE_GATED"


class LIFVoltageGatedChannel(Channel):

    def __init__(self, m_initial, reversal_potential, conductance, v_half, r,
                 activation_slope, deactivation_slope, equilibrium_slope):
        self.channel_type = Channel.LIF_VOLTAGE_GATED
        self.m_initial = reversal_potential
        self.reversal_potential = reversal_potential
        self.conductance = conductance
        self.v_half = v_half
        self.r = r
        self.activation_slope = activation_slope
        self.deactivation_slope = deactivation_slope
        self.equilibrium_slope = equilibrium_slope


class LIFCalciumDependentChannel(Channel):

    def __init__(self, m_initial, reversal_potential, conductance,
                 backwards_rate, forward_scale, forward_exponent, tau_scale):
        self.channel_type = Channel.LIF_CALCIUM_DEPENDENT
        self.m_initial = m_initial
        self.reversal_potential = reversal_potential
        self.conductance = conductance
        self.backwards_rate = backwards_rate
        self.forward_scale = forward_scale
        self.forward_exponent = forward_exponent
        self.tau_scale = tau_scale


class HHVoltageGatedChannel(Channel):

    def __init__(self):
        pass
