import unittest

import smoke_profile


def completed_save():
    return {
        'variables': {'blood_pact': 'completed', 'blood_pact_kayle': 'spared', 'blood_pact_caitlin': 'spared',
                      'blood_pact_reese': 'killed', 'quest_points': 1},
        'inventories': {'inventory': [{'id': 'kayles_sling'}, {'id': 'caitlins_staff'}, {'id': 'reeses_sword'}, {}],
                        'worn_equipment': [{'id': 'bronze_sword'}]},
        'experience': [1160, 1000, 1000, 11610, 1080, 0, 1000] + [0] * 18,
    }


class BloodPactSaveTests(unittest.TestCase):
    def test_earned_completion_is_accepted(self):
        smoke_profile.verify_blood_pact_save(completed_save())

    def test_missing_progress_loot_or_xp_is_rejected(self):
        for mutate in (
            lambda s: s['variables'].update(blood_pact='reese'),
            lambda s: s['variables'].update(blood_pact_caitlin='killed'),
            lambda s: s['inventories']['inventory'].remove({'id': 'reeses_sword'}),
            lambda s: s['inventories'].update(worn_equipment=[]),
            lambda s: s['experience'].__setitem__(6, 999),
        ):
            save = completed_save()
            mutate(save)
            with self.assertRaises(RuntimeError):
                smoke_profile.verify_blood_pact_save(save)


if __name__ == '__main__':
    unittest.main()
