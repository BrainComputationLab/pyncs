#import unittest
#import json
from pyncs import (Normal, IzhNeuron, Group, NeuronGroup, Geometry, Location,
                   FlatSynapse, Connection, Simulation, Simulator, Report,
                   RectCurrentStimulus)

izh = IzhNeuron(
    a=0.5,
    b=0.5,
    c=0.5,
    d=8.0,
    u=-12.0,
    v=Normal(-65.0, 0.5),
    #v=30.0,
    threshold=30.0
)

syn = FlatSynapse(
    delay=10.0,
    current=60.0
)

nrn_grp1 = NeuronGroup(
    neuron=izh,
    count=30,
    label="izh1",
    geometry=Geometry(),
    location=Location()
)
nrn_grp2 = NeuronGroup(
    neuron=izh,
    count=50,
    label="izh2",
    geometry=Geometry(),
    location=Location(),
)

conn = Connection(
    presynaptic="izh1",
    postsynaptic="izh2",
    probability=0.5,
    synapse=syn
)

grp = Group(
    entity_name="lolerskates",
    subgroups=[],
    neuron_groups=[nrn_grp1, nrn_grp2],
    neuron_aliases=[],
    synapse_aliases=[],
    connections=[conn]
)

stim = RectCurrentStimulus(
    amplitude=3.0,
    width=2,
    frequency=10,
    probability=0.6,
    time_start=0,
    time_end=1,
    destinations=["lolerskates:izh1"]
)

rpt = Report(
    report_method=Report.METHOD_FILE,
    report_type=Report.TYPE_NEURON,
    report_target=[nrn_grp1],
    probability=0.5,
    time_start=0.0,
    time_end=1.0
)

sim = Simulation(
    top_group=grp,
    stimuli=[stim],
    reports=[rpt]
)

server = Simulator(
    host='localhost',
    port=8000,
    username='bob',
    password='123456'
)

#d = server._generate_entity_dicts(sim.top_group, [stim], [])
#d = server._process_entity_dicts(sim.top_group, d)
#print json.dumps(d)

print "Getting server status"
print server.get_status()
print "Run mock sim"
print server.run(sim)


#print json.dumps(grp.to_dict())

#class TestTest(unittest.TestCase):
#
#    def test_1(self):
#        pass
