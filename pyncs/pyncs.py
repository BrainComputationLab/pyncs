import requests
import os
import json
import textwrap
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
            ('_id', [str]),
            ('entity_type', [str]),
            ('description', [str]),
            ('author', [str]),
            ('author_email', [str])
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
        # strip the types out for name checking
        params = map(lambda x: x[0], self.parameter_list)
        meta = map(lambda x: x[0], self.metadata)
        # if the key isn't in the parameter list/meta list, throw an error
        if key not in params and key not in meta:
            # Generate parameter list
            l = params + meta
            # list acceptable parameters for this entity
            raise TypeError(textwrap.dedent(
                "cannot assign attribute %s, "
                "acceptable attributes include %s" % (key, l))
            )
        # TODO This is a dumb way of doing this, need to reconsider
        # Check for type accuracy
        for param in self.parameter_list:
            # find the parameter in the list
            if param[0] is key:
                # if the specified type isn't allowed, throw an exception
                if type(value) not in param[1]:
                    raise TypeError(textwrap.dedent(
                        "invalid type of attribute %s (%s), acceptable "
                        "types include %s" % (key, type(value), param[1]))
                    )
                # otherwise we're done here
                else:
                    break
        self.__dict__[key] = value

    def to_dict(self):
        # create the dictionary object
        dictionary = {'specification': {}}
        params = map(lambda x: x[0], self.parameter_list)
        meta = map(lambda x: x[0], self.metadata)
        # create the metadata parameters
        for param in meta:
            try:
                attr = getattr(self, param)
                dictionary[param] = attr
            except AttributeError:
                continue
        # add the entity-specific parameters to the parameters property
        for param in params:
            try:
                attr = getattr(self, param)
                if type(attr) in [Normal, Uniform]:
                    dictionary['parameters'][param] = attr.to_dict()
                else:
                    dictionary['parameters'][param] = attr
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
        self.parameter_list += [('channel_type', [str])]
        kwargs['entity_type'] = _Entity.CHANNEL
        _Entity.__init__(self, kwargs)


class LIFVoltageGatedChannel(_Channel):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('v_half', [int, float, Normal, Uniform]),
            ('r', [int, float, Normal, Uniform]),
            ('activation_slope', [int, float, Normal, Uniform]),
            ('deactivation_slope', [int, float, Normal, Uniform]),
            ('equilibrium_slope', [int, float, Normal, Uniform]),
            ('conductance', [int, float, Normal, Uniform]),
            ('reversal_potential', [int, float, Normal, Uniform]),
            ('m_initial', [int, float, Normal, Uniform]),
            ('m_power', [int, float, Normal, Uniform])
        ]
        kwargs['channel_type'] = _Channel.LIF_VOLTAGE_GATED
        _Channel.__init__(self, kwargs)


class LIFCalciumDependentChannel(_Channel):

    def __init__(self, **kwargs):
        self.parameter_list += [
            ('m_initial', [int, float, Normal, Uniform]),
            ('reversal_potential', [int, float, Normal, Uniform]),
            ('conductance', [int, float, Normal, Uniform]),
            ('backwards_rate', [int, float, Normal, Uniform]),
            ('forward_scale', [int, float, Normal, Uniform]),
            ('forward_exponent', [int, float, Normal, Uniform]),
            ('backwards_rate', [int, float, Normal, Uniform]),
            ('tau_scale', [int, float, Normal, Uniform])
        ]
        kwargs['channel_type'] = _Channel.LIF_CALCIUM_DEPENDENT
        _Channel.__init__(self, kwargs)


class HHVoltageGatedChannel(_Channel):

    def __init__(self):
        # TODO: Write this!
        raise NotImplementedError()


class _Synapse(_Entity):

    FLAT = 'flat'
    NCS = 'ncs'

    def __init__(self, kwargs):
        self.parameter_list += [('synapse_type', [str])]
        kwargs['entity_type'] = _Entity.SYNAPSE
        _Entity.__init__(self, kwargs)


class FlatSynapse(_Synapse):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('delay', [int, float, Normal, Uniform]),
            ('current', [int, float, Normal, Uniform])
        ]
        kwargs['synapse_type'] = _Synapse.FLAT
        _Synapse.__init__(self, kwargs)


class NCSSynapse(_Synapse):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('utilization', [int, float, Normal, Uniform]),
            ('redistribution', [int, float, Normal, Uniform]),
            ('last_prefire_time', [int, float, Normal, Uniform]),
            ('last_postfire_time', [int, float, Normal, Uniform]),
            ('tau_facilitation', [int, float, Normal, Uniform]),
            ('tau_depression', [int, float, Normal, Uniform]),
            ('tau_ltp', [int, float, Normal, Uniform]),
            ('tau_ltd', [int, float, Normal, Uniform]),
            ('a_ltp_minimum', [int, float, Normal, Uniform]),
            ('a_ltd_minimum', [int, float, Normal, Uniform]),
            ('max_conductance', [int, float, Normal, Uniform]),
            ('reversal_potential', [int, float, Normal, Uniform]),
            ('tau_postsynaptic_conductance', [int, float, Normal, Uniform]),
            ('psg_waveform_duration', [int, float, Normal, Uniform]),
            ('delay', [int, float, Normal, Uniform])
        ]
        kwargs['synapse_type'] = _Synapse.NCS
        _Synapse.__init__(self, kwargs)


class _Stimulus(_Entity):

    RECTANGULAR_CURRENT = 'rectangular_current'

    def __init__(self, **kwargs):
        self.parameter_list += [('stimulus_type', [str])]
        self.parameter_list += [
            ('time_start', [int, float, Normal, Uniform]),
            ('time_end', [int, float, Normal, Uniform]),
            ('probability', [int, float, Normal, Uniform])
        ]
        kwargs['entity_type'] = _Entity.STIMULUS
        _Entity.__init__(self, kwargs)


class RectangularCurrentStimulus(_Stimulus):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('amplitude', [int, float, Normal, Uniform]),
            ('width', [int, float, Normal, Uniform]),
            ('frequency', [int, float, Normal, Uniform]),
        ]
        kwargs['stimulus_type'] = _Stimulus.RECTANGULAR_CURRENT
        _Stimulus.__init__(self, kwargs)


class Report(_Entity):

    FILE = 'file'
    SOCKET = 'socket'

    def __init__(self, **kwargs):
        self.parameter_list += [
            ('report_method', [str]),
            ('report_type', [str])
            ('report_target', [str]),
            ('probability', [float]),
            ('time_start', [int]),
            ('time_end', [int])
        ]
        kwargs['entity_type'] = _Entity.REPORT
        _Entity.__init__(self, kwargs)


class _Neuron(_Entity):

    IZH_NEURON = 'izh_neuron'
    NCS_NEURON = 'ncs_neuron'
    HH_NEURON = 'hh_neuron'

    def __init__(self, kwargs):
        self.parameter_list += [('neuron_type', [str])]
        kwargs['entity_type'] = _Entity.NEURON
        _Entity.__init__(self, kwargs)


class IzhNeuron(_Neuron):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('a', [int, float, Normal, Uniform]),
            ('b', [int, float, Normal, Uniform]),
            ('c', [int, float, Normal, Uniform]),
            ('d', [int, float, Normal, Uniform]),
            ('u', [int, float, Normal, Uniform]),
            ('v', [int, float, Normal, Uniform]),
            ('threshold', [int, float, Normal, Uniform])
        ]
        kwargs['neuron_type'] = _Neuron.IZH_NEURON
        _Neuron.__init__(self, kwargs)


class NCSNeuron(_Neuron):

    def __init__(self, **kwargs):
        self.parameter_list += [
            ('threshold', [int, float, Normal, Uniform]),
            ('spikeshape', [int, float, Normal, Uniform]),
            ('resting_potential', [int, float, Normal, Uniform]),
            ('calcium', [int, float, Normal, Uniform]),
            ('calcium_spike_increment', [int, float, Normal, Uniform]),
            ('tau_calcium', [int, float, Normal, Uniform]),
            ('leak_reversal_potential', [int, float, Normal, Uniform]),
            ('leak_conductance', [int, float, Normal, Uniform]),
            ('tau_membrane', [int, float, Normal, Uniform]),
            ('r_membrane', [int, float, Normal, Uniform]),
            ('channels', [list])
        ]
        kwargs['neuron_type'] = _Neuron.NCS_NEURON
        _Neuron.__init__(self, kwargs)

    def __setattr__(self, key, value):
        _Entity.__setattr__(self, key, value)
        if key is 'channels':
            for idx, channel in enumerate(value):
                if not issubclass(type(channel), _Channel):
                    raise EntityError("Invalid channel at index %d" % idx)


class HHNeuron(_Neuron):

    def __init__(self, **kwargs):
        self.parameter_list += [
            ('resting_potential', [int, float, Normal, Uniform]),
            ('threshold', [int, float, Normal, Uniform]),
            ('capacitance', [int, float, Normal, Uniform]),
            ('channels', [list])
        ]
        kwargs['neuron_type'] = _Neuron.HH_NEURON
        _Neuron.__init__(self, kwargs)

    def __setattr__(self, key, value):
        _Entity.__setattr__(self, key, value)
        if key is 'channels':
            for idx, channel in enumerate(value):
                if not issubclass(type(channel), _Channel):
                    raise EntityError("Invalid channel at index %d" % idx)


class Group(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('geometry', [dict]),
            ('subgroups', [list]),
            ('neuron_groups', [list]),
            ('neuron_aliases', [list]),
            ('synaptic_aliases', [list]),
            ('connections', [list])
        ]
        kwargs['entity_type'] = _Entity.GROUP
        _Entity.__init__(self, kwargs)

    def __setattr__(self, key, value):
        _Entity.__setattr__(self, key, value)
        if key is 'geometry':
            if 'width' not in value or 'height' not in value or 'depth' not in value:
                raise EntityError("Invalid geomeetry dict, check documentation")
        if key is 'subgroups':
            for idx, d in enumerate(value):
                if 'group' not in d or type(d['group_id']) is not Group:
                    raise EntityError("Invalid group spec at list index %d" % idx)
                if 'label' not in d or type(d['label']) is not str:
                    raise EntityError("Invalid group spec at list index %d" % idx)
                # Location is optional at this point
                if 'location' in d:
                    if type(d['location']) is not dict:
                        raise EntityError("Invalid group spec at list index %d" % idx)
                    if 'x' not in d['location']:
                        raise EntityError("Invalid group spec at list index %d" % idx)
                    if 'y' not in d['location']:
                        raise EntityError("Invalid group spec at list index %d" % idx)
                    if 'z' not in d['location']:
                        raise EntityError("Invalid group spec at list index %d" % idx)
        if key is 'neuron_groups':
            for idx, d in enumerate(value):
                if 'neuron' not in d or not issubclass(type(d['neuron']), _Neuron):
                    raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                if 'label' not in d or type(d['label']) is not str:
                    raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                if 'geometry' in d:
                    if type(d['geometry']) is not dict:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'width' not in d['geometry']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'height' not in d['geometry']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'depth' not in d['geometry']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                if 'location' in d:
                    if type(d['location']) is not dict:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'x' not in d['location']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'y' not in d['location']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
                    if 'z' not in d['location']:
                        raise EntityError("Invalid neuron_group spec at list index %d" % idx)
        if key is 'neuron_aliases' or key is 'synaptic_aliases':
            for idx, d in enumerate(value):
                if 'alias' not in d or type(d['alias']) is not str:
                    raise EntityError("Invalid alias spec at list index %d" % idx)
                if 'labels' not in d and 'aliases' not in d:
                    raise EntityError("Invalid alias spec at list index %d" % idx)
                if 'labels' in d:
                    if type(d['labels']) is not list:
                        raise EntityError("Invalid alias spec at list index %d" % idx)
                    for l in d['labels']:
                        if type(l) is not str:
                            raise EntityError("Invalid alias spec at list index %d" % idx)
                if 'aliases' in d:
                    if type(d['aliases']) is not list:
                        raise EntityError("Invalid alias spec at list index %d" % idx)
                    for l in d['aliases']:
                        if type(l) is not str:
                            raise EntityError("Invalid alias spec at list index %d" % idx)
        if key is 'connections':
            for idx, d in enumerate(value):
                if 'presynaptic' not in d or type(d['presynaptic']) is not str:
                    raise EntityError("Invalid connection spec at list index %d" % idx)
                if 'postsynaptic' not in d or type(d['postsynaptic']) is not str:
                    raise EntityError("Invalid connection spec at list index %d" % idx)
                if 'probability' not in d or type(d['probability']) is not float:
                    raise EntityError("Invalid connection spec at list index %d" % idx)
                if 'synapse' not in d or not issubclass(type(d['synapse']), _Synapse):
                    raise EntityError("Invalid connection spec at list index %d" % idx)
                if 'recurrent' in d and type(d['recurrent']) is not bool:
                    raise EntityError("Invalid connection spec at list index %d" % idx)
