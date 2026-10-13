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

    def test_kill_choices_survive_with_the_same_loot_and_rewards(self):
        save = completed_save()
        save['variables'].update(blood_pact_kayle='killed', blood_pact_caitlin='killed')
        smoke_profile.verify_blood_pact_save(save, kill_cultists=True)
        with self.assertRaises(RuntimeError):
            smoke_profile.verify_blood_pact_save(save)

    def test_kill_route_rejects_spared_or_unresolved_cultists(self):
        for cultist in ('blood_pact_kayle', 'blood_pact_caitlin'):
            for fate in ('spared', 'defeated', None):
                with self.subTest(cultist=cultist, fate=fate):
                    save = completed_save()
                    save['variables'].update(blood_pact_kayle='killed', blood_pact_caitlin='killed')
                    save['variables'][cultist] = fate
                    with self.assertRaises(RuntimeError):
                        smoke_profile.verify_blood_pact_save(save, kill_cultists=True)

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

    def test_mixed_fates_are_checked_per_cultist(self):
        save = completed_save()
        save['variables'].update(blood_pact_kayle='spared', blood_pact_caitlin='killed')
        smoke_profile.verify_blood_pact_save(save, kayle='spare', caitlin='kill')
        for kwargs in ({}, {'kayle': 'kill', 'caitlin': 'kill'}, {'kayle': 'kill', 'caitlin': 'spare'}, {'kill_cultists': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                smoke_profile.verify_blood_pact_save(save, **kwargs)

    def magic_save(self):
        save = completed_save()
        save['inventories']['inventory'] = [{'id': 'kayles_sling'}, {'id': 'reeses_sword'}, {'id': 'bronze_sword'}, {'id': 'mind_rune', 'amount': 11}]
        save['inventories']['worn_equipment'] = [{'id': 'caitlins_staff'}]
        save['experience'][6] = 1015
        return save

    def test_magic_route_needs_a_wielded_staff_casting_xp_and_spent_runes(self):
        smoke_profile.verify_blood_pact_save(self.magic_save(), magic=True)
        for mutate in (
            lambda s: s['inventories'].update(worn_equipment=[{'id': 'bronze_sword'}]),
            lambda s: s['experience'].__setitem__(6, 1000),
            lambda s: s['inventories']['inventory'].__setitem__(3, {'id': 'mind_rune', 'amount': 15}),
        ):
            save = self.magic_save()
            mutate(save)
            with self.assertRaises(RuntimeError):
                smoke_profile.verify_blood_pact_save(save, magic=True)


if __name__ == '__main__':
    unittest.main()
