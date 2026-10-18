"""Death-loot validation uses in-memory fixtures only; never reads real profiles or caches."""
import base64
import hashlib
import unittest

import death_loot_state as state
import profiles

GRAVE = '0f8fad5b-d9cb-469f-a165-000000000001'
PILE = '0f8fad5b-d9cb-469f-a165-000000000002'
GRAVE_BLOCK = f'''[[graves]]
id = "{GRAVE}"
account = "tester"
name = "Tester grave"
male = true
kind = "player_grave"
tile = 3221
direction = 0
remaining = 300
blessed = false
latest = true
'''
PILE_BLOCK = f'''[[piles]]
id = "{PILE}"
item = "bronze_sword"
amount = 1
charges = 0
tile = 3221
owner = ""
sources = ["tester"]
reveal = 0
disappear = 200
'''
PAYLOAD = GRAVE_BLOCK + '\n' + PILE_BLOCK


def envelope(payload=PAYLOAD, digest=None, extra=''):
    raw = payload.encode()
    digest = hashlib.sha256(raw).hexdigest() if digest is None else digest
    return ('format = 1\npayload = "' + base64.b64encode(raw).decode() + '"\nsha256 = "' + digest + '"\n' + extra).encode()


def native(name='Tester', version=None):
    prefix = '' if version is None else 'storage_version = ' + str(version) + '\n'
    return (prefix + 'accountName = "' + name + '"\npasswordHash = "fixture-hash"\nexperience = ' + str([0]*25) + '\nlevels = ' + str([1]*25) + '\nlooks = ' + str([0]*7) + '\ncolours = ' + str([0]*5) + '\n[tile]\nx = 3221\ny = 3219\n').encode()


def batch(members):
    rows = ''.join(f'{name}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\n' for name, data in sorted(members.items()))
    files = {'manifest.tsv': ('SOLOSCAPE_ACCOUNT_BATCH_V1\n' + rows).encode()}
    files.update(members)
    return {state.JOURNAL + '/' + name: data for name, data in files.items()}


def validate(contents):
    return state.validate_state(contents, profiles.validate_save)


class DeathLootStateTests(unittest.TestCase):
    def test_valid_world_envelope_returns_payload(self):
        payload = state.validate_world(envelope())
        self.assertEqual(payload['graves'][0]['id'], GRAVE)
        self.assertEqual(payload['piles'][0]['sources'], ['tester'])

    def test_malformed_envelopes_and_payloads_are_refused(self):
        bad_pile = PAYLOAD.replace('owner = ""', 'owner = "Ally"')
        cases = {
            'checksum': envelope(digest='0' * 64),
            'uppercase digest': envelope(digest=hashlib.sha256(PAYLOAD.encode()).hexdigest().upper()),
            'bool format': envelope().replace(b'format = 1', b'format = true'),
            'extra envelope key': envelope(extra='extra = 1\n'),
            'non-canonical base64': envelope().replace(b'payload = "', b'payload = " '),
            'owned pile with zero reveal': envelope(bad_pile),
            'duplicate grave id': envelope(PAYLOAD + '\n' + GRAVE_BLOCK),
            'two latest graves': envelope(PAYLOAD + '\n[[graves]]\nid = "0f8fad5b-d9cb-469f-a165-000000000003"\naccount = "tester"\nname = "Second"\nmale = true\nkind = "player_grave"\ntile = 1\ndirection = 0\nremaining = 1\nblessed = false\nlatest = true\n'),
            'bool tile': envelope(PAYLOAD.replace('tile = 3221\ndirection', 'tile = true\ndirection')),
            'nested pile source': envelope(PAYLOAD.replace('sources = ["tester"]', 'sources = [["tester"]]')),
            'duplicate pile sources': envelope(PAYLOAD.replace('sources = ["tester"]', 'sources = ["tester", "tester"]')),
            'grave and pile share id': envelope(PAYLOAD.replace(PILE, GRAVE)),
            'unknown payload key': envelope(PAYLOAD + 'extra = 1\n'),
        }
        for label, data in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    state.validate_world(data)

    def test_pending_batch_overrides_mixed_canonical_pair_and_keeps_logical_state(self):
        contents = {'saves/tester.toml': native(version=0), 'saves/other.toml': native('Other')}
        contents.update(batch({'tester.toml': native(version=1), state.WORLD_FILE: envelope()}))
        result = validate(contents)
        self.assertEqual(result['accounts']['tester']['storage_version'], 1)
        self.assertEqual(sorted(result['accounts']), ['other', 'tester'])
        self.assertEqual(len(result['world']['graves']), 1)

    def test_legacy_only_batch_is_valid_without_world(self):
        result = validate(batch({'tester.toml': native()}))
        self.assertIsNone(result['world'])
        self.assertEqual(list(result['accounts']), ['tester'])

    def test_storage_version_one_needs_a_world_file_in_journal_or_canonical_root(self):
        with self.assertRaisesRegex(ValueError, 'world'):
            validate({'saves/tester.toml': native(version=1)})
        with self.assertRaisesRegex(ValueError, 'world'):
            validate(batch({'tester.toml': native(version=1)}))
        self.assertIsNotNone(validate({'saves/tester.toml': native(version=1), 'saves/' + state.WORLD_FILE: envelope()})['world'])

    def test_corrupt_canonical_world_is_refused_when_it_is_the_logical_world(self):
        with self.assertRaises(ValueError):
            validate({'saves/tester.toml': native(version=1), 'saves/' + state.WORLD_FILE: envelope(digest='0' * 64)})

    def test_batch_members_must_match_manifest_exactly(self):
        good = batch({'tester.toml': native(version=0)})
        tampered = dict(good)
        tampered[state.JOURNAL + '/tester.toml'] = native('Tester', version=0).replace(b'Tester', b'Testex')
        extra = dict(good)
        extra[state.JOURNAL + '/stray.toml'] = native()
        nested = dict(good)
        nested[state.JOURNAL + '/sub/tester.toml'] = native()
        pending_file = dict(good)
        pending_file[state.JOURNAL] = b'not a directory'
        cases = {'checksum': tampered, 'unlisted file': extra, 'nested file': nested, 'pending file': pending_file,
                 'missing manifest': {k: v for k, v in good.items() if not k.endswith('manifest.tsv')}}
        for label, contents in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    validate(contents)

    def test_malformed_manifest_rows_are_refused(self):
        member = native()
        digest = hashlib.sha256(member).hexdigest()
        header = 'SOLOSCAPE_ACCOUNT_BATCH_V1\n'
        cases = {
            'bad header': b'SOLOSCAPE_ACCOUNT_BATCH_V2\n',
            'blank row': (header + '\n').encode(),
            'extra column': (header + f'tester.toml\t{len(member)}\t{digest}\textra\n').encode(),
            'uppercase digest': (header + f'tester.toml\t{len(member)}\t{digest.upper()}\n').encode(),
            'unsorted rows': (header + f'tester.toml\t{len(member)}\t{digest}\nalpha.toml\t{len(member)}\t{digest}\n').encode(),
            'missing trailing newline': (header + f'tester.toml\t{len(member)}\t{digest}').encode(),
            'non-ascii': (header + 'tëster.toml\t1\t' + digest + '\n').encode('utf-8'),
        }
        for label, manifest in cases.items():
            with self.subTest(case=label):
                contents = {state.JOURNAL + '/manifest.tsv': manifest, state.JOURNAL + '/tester.toml': member}
                with self.assertRaises(ValueError):
                    validate(contents)


if __name__ == '__main__':
    unittest.main()
