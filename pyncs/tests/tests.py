import unittest
from pyncs import Normal, LIFVoltageGatedChannel

har = Normal(1.0, 0.2)
print har.to_dict()

har = LIFVoltageGatedChannel(
    v_half=0.5,
    r=0.5,
    lolz=5.0
)

print har.to_dict()


class TestTest(unittest.TestCase):

    def test_1(self):
        pass
