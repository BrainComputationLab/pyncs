import requests
import os
import json
from urlparse import urlparse


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


class EntityError(Exception):

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
        # if they haven't authenticated throw an error
        if not self.token:
            return SimulationError("""Not authenticated, authenticate by
                                   calling the authenticate() function on this
                                   object before attempting to run a
                                   simulation""")
        # recurse through the top group and build the simulation json object
        entity_dicts = generate_entity_dicts(simulation.top_group)
        # set the username
        entity_dicts['meta'] = {'username': self.username}
        # which group is the top-level group
        entity_dicts['top_group'] = {"group_id": simulation.top_group['_id']}
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
    # check/add neuron types and channels
    for neuron_group in model.neuron_groups:
        # if the neuron isn't in the neuron list yet
        if neuron_group['neuron']._id not in entity_dicts['neuron_list']:
            # add it to the list
            entity_dicts['neuron_list'][neuron_group['neuron']._id] = \
                neuron_group['neuron']
            # check all of its channels
            for channel in neuron_group['neuron']['channels']:
                # if the channel isn't in the list, add it
                if channel._id not in entity_dicts['channel_list']:
                    entity_dicts['channel_list'][channel._id] = channel
    for alias in model.neuron_aliases:
        new_alias = alias.copy()
        new_alias['group_id'] = model._id
        # if the alias was already created, we have an error
        if new_alias['alias'] in entity_dicts['neuron_alias_list']:
            raise SimulationError("neuron alias already exists")
        # add it to the dicts
        else:
            entity_dicts['neuron_alias_list'][new_alias['alias']] = new_alias
    for alias in model.synapse_aliases:
        new_alias = alias.copy()
        new_alias['group_id'] = model._id
        # if the alias was already created, we have an error
        if new_alias['alias'] in entity_dicts['synapse_alias_list']:
            raise SimulationError("synapse alias already exists")
        # add it to the dicts
        else:
            entity_dicts['neuron_alias_list'][new_alias['alias']] = new_alias
    # recursively traverse the subgroups of the model
    for subgroup in model.subgroups:
        # call this function on the current subgroup and get the dict back
        res = subgroup_result_list.append(generate_entity_dicts(subgroup))
    # look at all the submodels resulting dictionaries
    for res in subgroup_result_list:
        # loop over the entity categories from the result (eg. neuron_dict)
        for entity_category, entity_category_dict in res:
            # loop over the entities created in that category
            for entity_id, entity_value in entity_category_dict:
                # add the new entities to their corresponding dictionary
                entity_dicts[entity_category][entity_id] = entity_value
    # return the resulting entity dictionary
    return entity_dicts


class Simulation(object):

    def __init__(self, top_group, stimuli, reports):
        self.top_group = top_group
        self.stimuli = stimuli
        self.reports = reports


class _Entity(object):

    STIMULUS = 'stimulus'
    GROUP = 'group'
    CHANNEL = 'channel'
    REPORT = 'report'
    SYNAPSE = 'synapse'
    NEURON = 'neuron'

    def __init__(self, kwargs):
        self.metadata = [
            '_id',
            'entity_type',
            'description',
            'author',
            'author_email'
        ]
        for param, value in kwargs.iteritems():
            setattr(self, param, kwargs[param])
        if '_id' not in kwargs:
            # this should have significant enough entropy to not cause
            # collisions within the next 40 years or so
            self._id = os.urandom(32).encode('hex')
        # Lock the parameter and metadata lists from changing at runtime
        self.locked = True

    def __setattr__(self, key, value):
        """ This ensures that the correct parameters are being set on the
        entities to prevent bugs, etc. """
        # if we're locking the entity, do it
        if key is 'locked':
            self.__dict__[key] = value
            return
        # if we're setting either of these lists, its okay if its not locked
        if (key is 'parameter_list' or key is 'metadata'
                and 'locked' not in self.__dict__):
            # set the value
            self.__dict__[key] = value
            return
        # if the key isn't in the parameter list, throw an error
        if key not in self.parameter_list and key not in self.metadata:
            # list acceptable parameters for this entity
            raise TypeError("""cannot assign this attribute, acceptable \
                            attributes include %s or %s"""
                            % (self.parameter_list, self.metadata))
        else:
            self.__dict__[key] = value

    def to_dict(self):
        # create the dictionary object
        dictionary = {'parameters': {}}
        # create the metadata parameters
        for param in self.metadata:
            try:
                dictionary[param] = getattr(self, param)
            except AttributeError:
                continue
        # add the entity-specific parameters to the parameters property
        for param in self.parameter_list:
            try:
                dictionary['parameters'][param] = getattr(self, param)
            except AttributeError:
                continue
        return dictionary


class Normal(object):
    """ Class for a normal distribution of a parameter """

    def __init__(self, mean, stdev):
        self.mean = mean
        self.stdev = stdev

    def to_dict(self):
        return {'mean': self.mean, 'stdev': self.stdev}


class Uniform(object):
    """ Class for a uniform distribution of a parameter """

    def __init__(self, min, max):
        self.min = min
        self.max = max

    def to_dict(self):
        return {'min': self.min, 'max': self.max}


class _Channel(_Entity):

    LIF_VOLTAGE_GATED = 'lif_voltage_gated'
    LIF_CALCIUM_DEPENDENT = 'lif_calcium_dependent'
    HH_VOLTAGE_GATED = 'hh_voltage_gated'

    def __init__(self, kwargs):
        kwargs['entity_type'] = _Entity.CHANNEL
        self.parameter_list += ['channel_type']
        _Entity.__init__(self, kwargs)


class LIFVoltageGatedChannel(_Channel):

    def __init__(self, **kwargs):
        self.parameter_list = [
            'v_half',
            'r',
            'activation_slope',
            'deactivation_slope',
            'equilibrium_slope',
            'conductance',
            'reversal_potential',
            'm_initial',
            'm_power'
        ]
        kwargs['channel_type'] = _Channel.LIF_VOLTAGE_GATED
        _Channel.__init__(self, kwargs)


class LIFCalciumDependentChannel(_Channel):

    def __init__(self, **kwargs):
        self.parameter_list += [
            'm_initial',
            'reversal_potential',
            'conductance',
            'backwards_rate',
            'forward_scale',
            'forward_exponent',
            'backwards_rate',
            'tau_scale'
        ]
        _Channel.__init__(self, kwargs)


class HHVoltageGatedChannel(_Channel):

    def __init__(self):
        # TODO: Write this!
        pass


class _Synapse(_Entity):

    FLAT = 'flat'
    NCS = 'ncs'

    def __init__(self, synapse_type, parameter_list):
        _Entity.__init__(self, entity_type=_Entity.SYNAPSE)
        self.synapse_type = synapse_type


class FlatSynapse(_Synapse):

    def __init__(self, delay, current):
        _Synapse.__init__(self, synapse_type=_Synapse.FLAT)
        self.parameter_list += [
            'delay',
            'current'
        ]
        self.delay = delay
        self.current = current


class NCSSynapse(_Synapse):

    def __init__(self, utilization, redistribution, last_prefire_time,
                 last_postfire_time, tau_facilitation, tau_depression, tau_ltp,
                 tau_ltd, a_ltp_minimum, a_ltd_minimum, max_conductance,
                 reversal_potential, tau_postsynaptic_conductance,
                 psg_waveform_duration, delay):
        _Synapse.__init__(self, synapse_type=_Synapse.NCS)
        self.parameter_list += [
            'utilization',
            'redistribution',
            'last_prefire_time',
            'last_postfire_time',
            'tau_facilitation',
            'tau_depression',
            'tau_ltp',
            'tau_ltd',
            'a_ltp_minimum',
            'a_ltd_minimum',
            'max_conductance',
            'reversal_potential',
            'tau_postsynaptic_conductance',
            'psg_waveform_duration',
            'delay'
        ]
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


class _Stimulus(_Entity):

    RECTANGULAR_CURRENT = 'rectangular_current'

    def __init__(self, stimulus_type, time_start, time_end, probability):
        _Entity.__init__(self, entity_type=_Entity.STIMULUS)
        self.parameter_list += [
            'time_start',
            'time_end',
            'probability'
        ]
        self.stimulus_type = stimulus_type
        self.time_start = time_start
        self.time_end = time_end
        self.probability = probability


class RectangularCurrentStimulus(_Stimulus):

    def __init__(self, amplitude, width, frequency, time_start, time_end,
                 probability):
        _Stimulus.__init__(self, _Stimulus.RECTANGULAR_CURRENT, time_start,
                           time_end, probability)
        self.parameter_list += [
            'amplitude',
            'width',
            'frequency',
        ]
        self.amplitude = amplitude
        self.width = width
        self.frequency = frequency


class Report(_Entity):

    FILE = 'file'
    SOCKET = 'socket'

    def __init__(self, report_method, report_type, report_target, probability,
                 frequency, time_start, time_end):
        _Entity.__init__(self, entity_type=_Entity.REPORT)
        self.parameter_list += [
            'report_method',
            'report_type'
            'report_target',
            'probability',
            'time_start',
            'time_end'
        ]
        self.report_method = report_method
        self.report_type = report_type
        self.report_target = report_target
        self.probability = probability
        self.frequency = frequency
        self.time_start = time_start
        self.time_end = time_end


class _Neuron(_Entity):

    IZH_NEURON = 'izh_neuron'
    NCS_NEURON = 'ncs_neuron'
    HH_NEURON = 'hh_neuron'

    def __init__(self, neuron_type):
        _Entity.__init__(self, entity_type=_Entity.NEURON)
        self.neuron_type = neuron_type


class IzhNeuron(_Neuron):

    def __init__(self, a, b, c, d, u, v, threshold):
        _Neuron.__init__(self, _Neuron.IZH_NEURON)
        self.parameter_list += [
            'a',
            'b',
            'c',
            'd',
            'u',
            'v',
            'threshold'
        ]
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.u = u
        self.v = v
        self.threshold = threshold


class NCSNeuron(_Neuron):

    def __init__(self, threshold, spikeshape, resting_potential, calcium,
                 calcium_spike_increment, tau_calcium,
                 leak_reversal_potential, leak_conductance, tau_membrane,
                 r_membrane, channels):
        _Neuron.__init__(self, _Neuron.NCS_NEURON)
        self.parameter_list += [
            'threshold',
            'spikeshape',
            'resting_potential',
            'calcium',
            'calcium_spike_increment',
            'tau_calcium',
            'leak_reversal_potential',
            'leak_conductance',
            'tau_membrane',
            'r_membrane',
            'channels'
        ]
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


class HHNeuron(_Neuron):

    def __init__(self, resting_potential, threshold, capacitance, channels):
        _Neuron.__init__(self, _Neuron.HH_NEURON)
        self.parameter_list += [
            'resting_potential',
            'threshold',
            'capacitance',
            'channels'
        ]
        self.resting_potential = resting_potential
        self.threshold = threshold
        self.capacitance = capacitance
        self.channels = channels


class Group(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            'geometry',
            'subgroups',
            'neuron_groups',
            'neuron_aliases',
            'synaptic_aliases',
            'connections'
        ]
        _Entity.__init__(self, kwargs)
