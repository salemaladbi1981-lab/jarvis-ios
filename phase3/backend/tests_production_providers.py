"""No registered placeholder may report a successful real action."""
import unittest
from main import gateway
from tools import Tool, ToolGateway

class ProviderTests(unittest.TestCase):
    def test_production_device_tools_are_explicitly_unavailable(self):
        for name in ['read-temperature', 'read-light-state', 'get-today-events']:
            result = gateway.execute(name, {})
            self.assertFalse(result['ok'], name)
            self.assertIn(result['error'], ['not_connected', 'device_calendar_required'])
            self.assertNotIn('result', result)

    def test_gateway_does_not_wrap_failed_or_mock_provider_in_success(self):
        gateway = ToolGateway()
        tool = Tool('test', 'test', [], '', {}, {}, 'low', 'none')
        for result in [{'ok': False, 'error': 'offline'}, {'mock': True, 'reading': '22'}]:
            gateway.register(tool, lambda _: result)
            self.assertFalse(gateway.execute('test', {})['ok'])

    def test_real_provider_result_remains_available(self):
        gateway = ToolGateway()
        gateway.register(Tool('test', 'test', [], '', {}, {}, 'low', 'none'), lambda _: {'reading': 21})
        self.assertTrue(gateway.execute('test', {})['ok'])

if __name__ == '__main__': unittest.main()
