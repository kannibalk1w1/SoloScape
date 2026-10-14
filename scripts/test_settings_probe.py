"""Contract tests for the focused Settings ownership probe (source-level; the native run is `smoke-profile.sh --settings`)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = (ROOT / 'scripts/harness/NativeAdventureProbe.java').read_text()
SMOKE = (ROOT / 'scripts/smoke_profile.py').read_text()


class SettingsProbeContract(unittest.TestCase):
    def test_polling_pause_is_scoped_and_always_restored(self):
        self.assertIn('failedField.setBoolean(plugin,true)', PROBE)
        self.assertIn('failedField.setBoolean(plugin,false)', PROBE)
        # Failure path and success path both restore polling.
        self.assertRegex(PROBE, r'catch\(Exception ex\)\{padOff\(\);')
        self.assertRegex(PROBE, r'results\.put\("settings_back_to_home",true\);padOff\(\);')

    def test_uses_real_plugin_tick_not_direct_ui_updates(self):
        self.assertIn('processInput', PROBE)
        self.assertNotIn('ui.update(new GamepadState()', PROBE)

    def test_b_is_one_tick_pulse_after_a_neutral_beat(self):
        steps = dict(re.findall(r'if\(step==(10\d)\)\{(.*?)\n   \}', PROBE, re.S))
        self.assertIn('padHeld=2', steps['101'])      # neutral beat, then B
        self.assertIn('padHeld=0', steps['102'])      # released on the next tick
        self.assertIn('padTicks<padMark+3', steps['101'])

    def test_settings_flag_wiring(self):
        self.assertIn('--settings', SMOKE)
        self.assertIn('options.settings:options.adventure=True', SMOKE)
        self.assertIn("-Dsoloscape.settings.probe=true", SMOKE)
        self.assertIn('Boolean.getBoolean("soloscape.settings.probe")', PROBE)

    def test_home_ancestry_is_checked_on_the_radial(self):
        self.assertIn('radial.selected()==HomeTab.SETTINGS.ordinal()', PROBE)


if __name__ == '__main__':
    unittest.main()
