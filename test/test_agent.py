import unittest
from legacyhelper.core.agent import Agent

class TestAgent(unittest.TestCase):
    def test_agent_initialization(self):
        # This test will fail if the GEMINI_API_KEY is not set.
        # For now, we'll just check if the Agent can be instantiated.
        try:
            agent = Agent()
            self.assertIsInstance(agent, Agent)
        except ValueError as e:
            self.assertEqual(str(e), "GEMINI_API_KEY not found in environment variables.")

if __name__ == '__main__':
    unittest.main()
