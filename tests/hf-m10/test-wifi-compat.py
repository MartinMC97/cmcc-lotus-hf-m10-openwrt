#!/usr/bin/env python3
"""Station identity migration tests; never accesses a device or real UCI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-base/files/98-cmcc-lotus-hf-m10-wifi-compat'
UCI = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
path = Path(os.environ['TEST_UCI_STATE'])
state = json.loads(path.read_text())
args = sys.argv[1:]
if args and args[0] == '-q': args = args[1:]
action = args.pop(0)
if action == 'show':
    for key, value in state.items():
        print('wireless.' + key + '=' + value)
elif action == 'get':
    key = args[0].removeprefix('wireless.')
    if key not in state: sys.exit(1)
    print(state[key])
elif action == 'set':
    key, value = args[0].removeprefix('wireless.').split('=', 1)
    state[key] = value
    path.write_text(json.dumps(state))
elif action == 'commit':
    with Path(os.environ['TEST_UCI_COMMITS']).open('a') as out: out.write('commit\\n')
else:
    sys.exit(2)
'''


class StationIdentityTests(unittest.TestCase):
    def fixture(self):
        return {
            'radio0': 'wifi-device',
            'radio0.path': 'platform/ff4a0000.mmc/mmc_host/mmc0/mmc0:0001/mmc0:0001:1',
            'radio0.macaddr': '02:00:00:00:00:10',
            'station': 'wifi-iface', 'station.device': 'radio0',
            'station.mode': 'sta', 'station.network': 'wwan',
            'station.ssid': 'example-network', 'station.key': 'opaque-existing-key',
        }

    def migrate(self, state, repeats=1):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            config = tmp / 'wireless.json'; config.write_text(json.dumps(state))
            uci = tmp / 'uci'; uci.write_text(UCI); uci.chmod(0o755)
            commits = tmp / 'commits'
            env = {**os.environ, 'PATH': str(tmp) + ':' + os.environ['PATH'],
                   'TEST_UCI_STATE': str(config), 'TEST_UCI_COMMITS': str(commits)}
            for _ in range(repeats):
                result = subprocess.run(['sh', str(SCRIPT)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(config.read_text()), commits.read_text().count('commit') if commits.exists() else 0

    def test_each_units_saved_address_reaches_legacy_station(self):
        for address in ('02:00:00:00:00:10', '02:00:00:00:00:20'):
            with self.subTest(address=address):
                state = self.fixture(); state['radio0.macaddr'] = address
                result, commits = self.migrate(state)
                self.assertEqual(result['station.macaddr'], address)
                self.assertEqual(result['station.ifname'], 'wlan0')
                self.assertEqual(commits, 1)
                for key, value in state.items(): self.assertEqual(result[key], value)

    def test_explicit_interface_and_address_preserved(self):
        state = self.fixture()
        state.update({'station.ifname': 'custom-sta', 'station.macaddr': '02:00:00:00:00:30'})
        self.assertEqual(self.migrate(state), (state, 0))

    def test_explicit_legacy_station_address_preserved(self):
        for address in ('02:00:00:00:00:30', 'random'):
            state = self.fixture(); state.update({'station.ifname': 'wlan0', 'station.macaddr': address})
            self.assertEqual(self.migrate(state), (state, 0))

    def test_invalid_or_multicast_addresses_never_copied(self):
        for address in ('00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff', '01:00:00:00:00:10', 'invalid', ''):
            state = self.fixture(); state.update({'station.ifname': 'wlan0', 'radio0.macaddr': address})
            self.assertEqual(self.migrate(state), (state, 0))

    def test_additional_station_does_not_duplicate_name_or_address(self):
        state = self.fixture()
        state.update({'secondary': 'wifi-iface', 'secondary.device': 'radio0',
                      'secondary.mode': 'sta', 'secondary.network': 'wwan'})
        result, _ = self.migrate(state)
        self.assertEqual(result['station.ifname'], 'wlan0')
        self.assertNotIn('secondary.ifname', result)
        self.assertNotIn('secondary.macaddr', result)

    def test_other_networks_modes_and_radios_preserved(self):
        for key, value in [('station.network', 'guest'), ('station.mode', 'ap'), ('radio0.path', 'platform/usb')]:
            state = self.fixture(); state[key] = value
            self.assertEqual(self.migrate(state), (state, 0))

    def test_missing_wireless_config_is_unchanged(self):
        self.assertEqual(self.migrate({}), ({}, 0))

    def test_rerun_does_not_commit_again(self):
        result, commits = self.migrate(self.fixture(), repeats=2)
        self.assertEqual(commits, 1)
        self.assertEqual(result['station.ifname'], 'wlan0')

    def test_existing_wlan0_on_another_interface_is_respected(self):
        state = self.fixture(); state.update({'other': 'wifi-iface', 'other.ifname': 'wlan0'})
        self.assertEqual(self.migrate(state), (state, 0))

    def test_no_unit_address_is_invented(self):
        state = self.fixture(); del state['radio0.macaddr']
        result, _ = self.migrate(state)
        self.assertEqual(result['station.ifname'], 'wlan0')
        self.assertNotIn('station.macaddr', result)


if __name__ == '__main__':
    unittest.main()
