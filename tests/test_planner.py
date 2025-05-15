import unittest
from autocoder.common import AutoCoderArgs
from autocoder.agent.planner import Planner


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.args = AutoCoderArgs()
        self.planner = Planner(self.args, None)

    def test_empty(self):
        pass
