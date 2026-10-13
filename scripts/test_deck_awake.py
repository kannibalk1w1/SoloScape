import types
import unittest
from unittest.mock import Mock, patch
from deck_awake import keep_awake


class DisplayInhibitionTest(unittest.TestCase):
    def fake(self, interface):
        bus = Mock()
        module = types.SimpleNamespace(SessionBus=Mock(return_value=bus), Interface=Mock(return_value=interface))
        return module, bus

    def test_world_failure_releases_only_our_inhibition(self):
        interface = Mock()
        interface.Inhibit.return_value = 37
        module, bus = self.fake(interface)
        with patch.dict('sys.modules', {'dbus': module}):
            with self.assertRaisesRegex(RuntimeError, 'world failure'):
                with keep_awake() as status:
                    self.assertTrue(status['inhibited'])
                    bus.close.assert_not_called()
                    raise RuntimeError('world failure')
        interface.UnInhibit.assert_called_once_with(37, timeout=5)
        bus.close.assert_called_once()
        module.SessionBus.assert_called_once_with(private=True)

    def test_unsupported_desktop_does_not_block_the_session(self):
        interface = Mock()
        interface.Inhibit.side_effect = RuntimeError('no provider')
        module, bus = self.fake(interface)
        with patch.dict('sys.modules', {'dbus': module}):
            with keep_awake() as status:
                self.assertFalse(status['inhibited'])
        interface.UnInhibit.assert_not_called()
        bus.close.assert_called_once()
