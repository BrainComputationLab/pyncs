import requests
import os
import json
import textwrap


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

    STATUS_RUNNING = 'running'
    STATUS_IDLE = 'idle'

    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.is_authenticated = False
        self.url = 'http://' + self.host

    def authenticate(self):
        url = self.url
        url = url + "/login"
        auth_payload = {
            'username': self.username,
            'password': self.password
        }
        # attempt to connect to server
        try:
            r = requests.post(url, data=json.dumps(auth_payload))
        # if it doesn't work, alert the user
        except requests.exceptions.ConnectionError:
            raise AuthenticationError("Could not connect to authenticate")
        # otherwise load the data
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
        entity_dicts = self._generate_entity_dicts(simulation.top_group,
                                                   simulation.stimuli,
                                                   simulation.reports)
        # generate the proper transfer format
        transfer_format = self._process_entity_dicts(entity_dicts)
        # which group is the top-level group
        transfer_format['top_group'] = simulation.top_group._id
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

    # TODO Make this less complicated, CC is too high
    def _generate_entity_dicts(self, model, stimuli, reports):
        entity_dicts = {
            'neurons': {},
            'reports': {},
            'stimuli': {},
            'synapses': {},
            'groups': {},
            'neuron_aliases': {},
            'synapse_aliases': {}
        }
        subgroup_result_list = []
        # check the current
        if model._id not in entity_dicts['groups']:
            entity_dicts['groups'][model._id] = model
        # check/add neuron types and channels
        for neuron_group in model.neuron_groups:
            # if the neuron isn't in the neuron list yet
            if neuron_group.neuron._id not in entity_dicts['neurons']:
                # add it to the list
                entity_dicts['neurons'][neuron_group.neuron._id] = \
                    neuron_group.neuron
        # TODO Implement
        for alias in model.neuron_aliases:
            pass
        # TODO Implement
        for alias in model.synapse_aliases:
            pass
        # check/add stimulus types
        for stimulus in stimuli:
            if stimulus._id not in entity_dicts['stimuli']:
                entity_dicts['stimuli'][stimulus._id] = stimulus
        # add reports
        for report in reports:
            if report._id not in entity_dicts['reports']:
                entity_dicts['reports'][report._id] = report
        # recursively traverse the subgroups of the model
        for subgroup in model.subgroups:
            # call this function on the current subgroup and get the dict back
            res = subgroup_result_list.append(
                self._generate_entity_dicts(subgroup)
            )
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

    def _process_entity_dicts(self, entity_dicts):
        transfer_format = {
            'neurons': [],
            'reports': [],
            'stimuli': [],
            'synapses': [],
            'groups': [],
            'neuron_aliases': [],
            'synapse_aliases': []
        }
        # add them to lists
        for entity_type, entities in entity_dicts.iteritems():
            for entity_id, entity in entities.iteritems():
                transfer_format[entity_type].append(entity.to_dict())
        return transfer_format



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
            ('entity_name', [str]),
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
                # These types of attributes need special processing
                if type(attr) in [Normal, Uniform, NeuronGroup, Alias,
                                  Location, Geometry, Connection]:
                    dictionary['specification'][param] = attr.to_dict()
                else:
                    dictionary['specification'][param] = attr
            except AttributeError:
                continue
        return dictionary

    def is_valid(self):
        # iterate over the parameters
        for param in self.parameter_list:
            # if its not specified, we're invalid
            if param not in self.__dict__:
                return False
        return True


class Normal(object):
    """ Class for a normal distribution of a parameter """

    def __init__(self, mean, stdev):
        self.mean = mean
        self.stdev = stdev

    def to_dict(self):
        return {'type': 'normal', 'mean': self.mean, 'stdev': self.stdev}


class Uniform(object):
    """ Class for a uniform distribution of a parameter """

    def __init__(self, min, max):
        self.min = min
        self.max = max

    def to_dict(self):
        return {'type': 'uniform', 'min': self.min, 'max': self.max}


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

    def __init__(self, kwargs):
        self.parameter_list += [('stimulus_type', [str])]
        self.parameter_list += [
            ('time_start', [int, float, Normal, Uniform]),
            ('time_end', [int, float, Normal, Uniform]),
            ('probability', [int, float, Normal, Uniform])
        ]
        kwargs['entity_type'] = _Entity.STIMULUS
        _Entity.__init__(self, kwargs)


class RectCurrentStimulus(_Stimulus):

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
            ('geometry', [Geometry]),
            ('subgroups', [list]),
            ('neuron_groups', [list]),
            ('neuron_aliases', [list]),
            ('synapse_aliases', [list]),
            ('connections', [list])
        ]
        kwargs['entity_type'] = _Entity.GROUP
        if 'geometry' not in kwargs:
            kwargs['geometry'] = Geometry()
        _Entity.__init__(self, kwargs)

    def to_dict(self):
        d = _Entity.to_dict(self)
        spec = {
            'geometry': self.geometry.to_dict(),
            'subgroups': [x.to_dict() for x in self.subgroups],
            'neuron_groups': [x.to_dict() for x in self.neuron_groups],
            'neuron_aliases': [x.to_dict() for x in self.neuron_aliases],
            'synaptic_aliases': [x.to_dict() for x in self.synapse_aliases],
            'connections': [x.to_dict() for x in self.connections]
        }
        d['specification'] = spec
        return d


class SubGroup(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('group', [Group]),
            ('label', [str]),
            ('location', [Location])
        ]
        if 'location' not in kwargs:
            kwargs['location'] = Location()
        _Entity.__init__(self, kwargs)

    def to_dict(self):
        d = {
            'group': self.group._id,
            'label': self.label,
            'location': self.location.to_dict()
        }
        return d


class Geometry(object):

    def __init__(self, width=0.0, height=0.0, depth=0.0):
        self.width = width
        self.height = height
        self.depth = depth

    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'depth': self.depth
        }


class Location(object):

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def to_dict(self):
        return {'x': self.x, 'y': self.y, 'z': self.z}


class NeuronGroup(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('neuron', [IzhNeuron, NCSNeuron, HHNeuron]),
            ('count', [int]),
            ('label', [str]),
            ('geometry', [Geometry]),
            ('location', [Location])
        ]
        if 'geometry' not in kwargs:
            kwargs['geometry'] = Geometry()
        if 'location' not in kwargs:
            kwargs['location'] = Location()
        _Entity.__init__(self, kwargs)

    def to_dict(self):
        return {
            'neuron': self.neuron._id,
            'count': self.count,
            'label': self.label,
            'geometry': self.geometry.to_dict(),
            'location': self.location.to_dict()
        }


class Alias(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('alias', [str]),
            ('labels', [list]),
            ('aliases', [list])
        ]
        _Entity.__init__(self, kwargs)

    def __setattr__(self, key, value):
        _Entity.__setattr__(self, key, value)
        if key is 'labels':
            for idx, l in value:
                if type(l) is not str:
                    raise EntityError("invalid label at index %d" % idx)
        if key is 'aliases':
            for idx, a in value:
                if type(a) is not str:
                    raise EntityError("invalid alias at index %d" % idx)

    def to_dict(self):
        d = {
            'alias': self.alias,
            'labels': self.labels,
            'aliases': self.aliases
        }
        return d


class Connection(_Entity):

    def __init__(self, **kwargs):
        self.parameter_list = [
            ('presynaptic', [str]),
            ('postsynaptic', [str]),
            ('probability', [float]),
            ('synapse', [FlatSynapse, NCSSynapse]),
            ('recurrent', [bool])
        ]
        if 'recurrent' not in kwargs:
            kwargs['recurrent'] = False
        _Entity.__init__(self, kwargs)

    def __setattr__(self, key, value):
        _Entity.__setattr__(self, key, value)
        if key is 'probability' and (value > 1 or not value > 0):
            raise EntityError("probability must greater than 0 and less than "
                              "or equal to one")

    def to_dict(self):
        d = {
            'presynaptic': self.presynaptic,
            'postsynaptic': self.postsynaptic,
            'probability': self.probability,
            'synapse': self.synapse._id,
            'recurrent': self.recurrent
        }
        return d
