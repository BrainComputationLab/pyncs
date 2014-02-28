import requests
import os
import json
from urllib.parse import urlparse as urlparse


class AuthenticationError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return (self.value)


class SimulationError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return (self.value)


class Simulator(object):

    STATUS_RUNNING = 'STATUS_RUNNING'
    STATUS_IDLE = 'STATUS_IDLE'

    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.is_authenticated = False
        url = urlparse(host)
        if not url.port:
            url.port = port
        self.url = url

    def authenticate(self):
        self.url.path = "/login"
        auth_payload = {
            'username': self.username,
            'password': self.password
        }
        r = requests.post(self.url.get_url(), data=json.dumps(auth_payload))
        res = json.loads(r.text)
        if 'token' not in res:
            raise AuthenticationError("Authentication Failed")
        else:
            self.token = res['token']

    def get_status(self):
        self.url.path = "/sim"
        r = requests.get(self.url.get_url())
        res = json.loads(r.text)
        if res['status'] is 'idle':
            return Simulator.STATUS_IDLE
        if res['status'] is 'running':
            return Simulator.STATUS_RUNNING

    def run(self, simulation):
        # recurse through the model and build the simulation json object
        entity_dicts = generate_entity_dicts(simulation.model)
        # set the username
        entity_dicts['meta'] = {'username': self.username}
        # dump the dictionary to a json string
        sim_string = json.dumps(entity_dicts)
        # set the correct url path
        self.url.path = '/sim'
        # add the auth token to the request headers
        headers = {'token': self.token}
        # send the sim request
        r = requests.post(self.url.get_url(), data=sim_string, headers=headers)
        # if its not successful raise an exception
        if r.status_code is not 200:
            raise SimulationError(r.json()['message'])
        # otherwise return info about the simulation from ncsdaemon
        else:
            return r.json()


def generate_entity_dicts(self, model):
    entity_dicts = {
        'neuron_list': {},
        'channel_list': {},
        'report_list': {},
        'stimuli_list': {},
        'synapse_list': {},
        'group_list': {},
        'neuron_alias_list': {},
        'synapse_alias_list': {}
    }
    subgroup_result_list = []
    # check the current
    if model._id not in entity_dicts['group_list']:
        entity_dicts['group_list'][model['_id']] = model
    else:
        raise SimulationError("Recursive groups detected!")
        return
    # check/add neuron types and channels
    for neuron_group in model.neuron_groups:
        # if the neuron isn't in the neuron list yet
        if neuron_group['neuron']._id not in entity_dicts['neuron_list']:
            # add it to the list
            entity_dicts['neuron_list'][neuron_group['neuron']._id] = neuron_group['neuron']
            # check all of its channels
            for channel in neuron_group['neuron']['channels']:
                # if the channel isn't in the list, add it
                if channel._id not in entity_dicts['channel_list']:
                    entity_dicts['channel_list'][channel._id] = channel
    for alias in model.neuron_aliases:
        # TODO
        pass

    # recursively traverse the subgroups of the model
    for subgroup in model.subgroups:
        subgroup_result_list.append(generate_entity_dicts(subgroup))


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


class Neuron(Entity):

    IZH_NEURON = 'IZH_NEURON'
    NCS_NEURON = 'NCS_NEURON'
    HH_NEURON = 'HH_NEURON'

    def __init__(self, neuron_type):
        Entity.__init__(self, entity_type=Entity.NEURON)
        self.neuron_type = neuron_type


class IzhNeuron(Neuron):

    def __init__(self, a, b, c, d, u, v, threshold):
        Neuron.__init__(self, Neuron.IZH_NEURON)
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.u = u
        self.v = v
        self.threshold = threshold


class NCSNeuron(Neuron):

    def __init__(self, threshold, spikeshape, resting_potential, calcium,
                 calcium_spike_increment, tau_calcium,
                 leak_reversal_potential, leak_conductance, tau_membrane,
                 r_membrane, channels):
        Neuron.__init__(self, Neuron.NCS_NEURON)
        self.threshold = threshold
        self.spikeshape = spikeshape
        self.resting_potential = resting_potential
        self.calcium = calcium
        self.calcium_spike_increment = calcium_spike_increment
        self.tau_calcium = tau_calcium
        self.leak_reversal_potential = leak_reversal_potential
        self.leak_conductance = leak_conductance
        self.tau_membrane = tau_membrane
        self.r_membrane = r_membrane
        self.channels = channels


class HHNeuron(Neuron):

    def __init__(self, resting_potential, threshold, capacitance, channels):
        Neuron.__init__(self, Neuron.HH_NEURON)
        self.resting_potential = resting_potential
        self.threshold = threshold
        self.capacitance = capacitance
        self.channels = channels


class GroupType(Entity):

    def __init__(self, geometry, subgroups, neuron_groups, neuron_aliases,
                 synaptic_aliases, connections):
        Entity.__init__(self, entity_type=Entity.GROUP)
        self.geometry = geometry
        self.subgroups = subgroups
        self.neuron_groups = neuron_groups
        self.neuron_aliases = neuron_aliases
        self.synaptic_aliases = synaptic_aliases
        self.connections = connections


class GroupInstance(object):

    def __init__(self, group_type):
        pass
