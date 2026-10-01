"""Every registered specialist resolves to a real profile and an honest runtime event."""
import json
from pathlib import Path
import unittest
import agent_profiles
from agent_runtime import AgentRuntime

class AgentActivationTests(unittest.TestCase):
    def setUp(self): self.runtime = AgentRuntime()

    def test_all_21_registry_ids_have_execution_profiles(self):
        self.assertEqual(len(self.runtime.agent_ids), 21)
        self.assertEqual(set(self.runtime.agent_ids), set(agent_profiles.agent_ids()))
        app = Path(__file__).resolve().parents[2] / 'JARVIS/Resources/AGENT-REGISTRY.json'
        self.assertEqual(set(self.runtime.agent_ids), {a['id'] for a in json.loads(app.read_text())['agents']})

    def test_explicit_specialist_tool_drives_the_correct_visible_agent(self):
        for agent in self.runtime.agent_ids:
            routed = self.runtime.agent_for_tool('jarvis_agent', {'agent_id': agent})
            self.assertEqual(routed, agent)
            self.assertEqual(self.runtime.event_payload('started', routed)['agent_id'], agent)

    def test_invalid_specialist_does_not_invent_an_orbit_node(self):
        for args in [{}, {'agent_id': 'nonexistent'}, {'agent_id': None}]:
            self.assertEqual(self.runtime.agent_for_tool('jarvis_agent', args), 'core_coordinator')

    def test_provider_routes_remain_unchanged(self):
        for tool, agent in {'email_send': 'core_writer', 'email_search': 'core_coordinator',
                            'telegram_read': 'sys_circle', 'youtube_search': 'core_producer',
                            'instagram_profile': 'ct_mkt', 'maps_search': 'core_coordinator'}.items():
            self.assertEqual(self.runtime.agent_for_tool(tool), agent)

if __name__ == '__main__': unittest.main()
