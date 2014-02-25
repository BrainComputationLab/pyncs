import requests
import os
import hashlib


class Simulator(object):

    STATUS_RUNNING = 'STATUS_RUNNING'
    STATUS_IDLE = 'STATUS_IDLE'

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

    STIMULUS = 'STIMULUS'
    GROUP = 'GROUP'
    CHANNEL = 'CHANNEL'
    REPORT = 'REPORT'
    SYNAPSE = 'SYNAPSE'
    NEURON = 'NEURON'

    def __init__(self, _id, entity_type, entity_name, description, author,
                 author_email):
        self.parameter_list = [
            '_id',
            'entity_type',
            'description',
            'author',
            'author_email'
        ]
        if not _id:
            # this should have significant enough entropy to not cause
            # collisions within the next 3 billion years or so
            self._id = os.urandom(32).encode('hex')
        else:
            self._id = _id
        self.entity_type = entity_type
        self.description = description
        self.author = author
        self.author_email = author_email

    def __setattr__(self, key, value):
        """ This ensures that the correct parameters are being set on the
        entities to prevent bugs, etc. """
        # if the key isn't in the parameter list, throw an error
        if key not in self.parameter_list:
            # list acceptable parameters for this entity
            raise TypeError("""cannot assign this attribute, acceptable
                            attributes include %s""" % self.parameter_list)

    def to_dict():
        return {}


class Normal(Entity):
    ''' Class for a normal distribution of a parameter '''

    def __init__(self, mean, stdev):
        self.mean = mean
        self.stdev = stdev


class Uniform(Entity):
    ''' Class for a uniform distribution of a parameter '''

    def __init__(self, min, max):
        self.min = min
        self.max = max


class Neuron(Entity):
    ''' Class for the neuron entity '''

    def __init__(self, neuron_type):
        self.neuron_type = neuron_type


class Channel(Entity):

    LIF_VOLTAGE_GATED = 'LIF_VOLTAGE_GATED'
    LIF_CALCIUM_DEPENDENT = 'LIF_CALCIUM_DEPENDENT'
    HH_VOLTAGE_GATED = 'HH_VOLTAGE_GATED'

    def __init__(self, channel_type):
        Entity.__init__(self, entity_type=Entity.CHANNEL)
        self.channel_type = channel_type


class LIFVoltageGatedChannel(Channel):

    def __init__(self, m_initial, reversal_potential, conductance, v_half, r,
                 activation_slope, deactivation_slope, equilibrium_slope):
        Channel.__init__(self, channel_type=Channel.LIF_VOLTAGE_GATED)
        self.m_initial = m_initial
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
        Channel.__init__(self, channel_type=Channel.LIF_CALCIUM_DEPENDENT)
        self.m_initial = m_initial
        self.reversal_potential = reversal_potential
        self.conductance = conductance
        self.backwards_rate = backwards_rate
        self.forward_scale = forward_scale
        self.forward_exponent = forward_exponent
        self.tau_scale = tau_scale


class HHVoltageGatedChannel(Channel):

    def __init__(self):
        # TODO: Write this!
        pass


class Synapse(Entity):

    FLAT = 'FLAT'
    NCS = 'NCS'

    def __init__(self, synapse_type):
        Entity.__init__(self, entity_type=Entity.SYNAPSE)
        self.synapse_type = synapse_type


class FlatSynapse(Synapse):

    def __init__(self, delay, current):
        Synapse.__init__(self, synapse_type=Synapse.FLAT)
        self.parameter_list += [
            'delay',
            'current'
        ]
        self.delay = delay
        self.current = current


class NCSSynapse(Synapse):

    def __init__(self, utilization, redistribution, last_prefire_time,
                 last_postfire_time, tau_facilitation, tau_depression, tau_ltp,
                 tau_ltd, a_ltp_minimum, a_ltd_minimum, max_conductance,
                 reversal_potential, tau_postsynaptic_conductance,
                 psg_waveform_duration, delay):
        Synapse.__init__(self, synapse_type=Synapse.NCS)
        self.utilization = utilization
        self.redistribution = redistribution
        self.last_prefire_time = last_prefire_time
        self.last_postfire_time = last_postfire_time
        self.tau_facilitation = tau_facilitation
        self.tau_depression = tau_depression
        self.tau_ltp = tau_ltp
        self.tau_ltd = tau_ltd
        self.a_ltp_minimum = a_ltp_minimum
        self.a_ltd_minimum = a_ltd_minimum
        self.max_conductance = max_conductance
        self.reversal_potential = reversal_potential
        self.tau_postsynaptic_conductance = tau_postsynaptic_conductance
        self.psg_waveform_duration = psg_waveform_duration
        self.delay = delay


class Stimulus(Entity):

    def __init__(self, stimulus_type, time_start, time_end, probability):
        Entity.__init__(self, entity_type=Entity.STIMULUS)
        self.stimulus_type = stimulus_type
        self.time_start = time_start
        self.time_end = time_end
        self.probability = probability


class RectangularCurrentStimulus(Stimulus):

    def __init__(self, amplitude, width, frequency, time_start, time_end,
                 probability):
        Stimulus.__init__(self, Stimulus.RECTANGULAR_CURRENT, time_start,
                          time_end, probability)
        self.amplitude = amplitude
        self.width = width
        self.frequency = frequency


class Report(Entity):

    FILE = 'FILE'
    SOCKET = 'SOCKET'

    def __init__(self, report_method, report_type, report_target, probability,
                 frequency, time_start, time_end):
        self.report_method = report_method
        self.report_type = report_type
        self.report_target = report_target
        self.probability = probability
        self.frequency = frequency
        self.time_start = time_start
        self.time_end = time_end
