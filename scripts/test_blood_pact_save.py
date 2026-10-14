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


class OvernightRouteSaveTests(unittest.TestCase):
    def test_xp_scaling_is_exact(self):
        save = {'experience': [0] * 8 + [2500] + [0] * 16}
        smoke_profile.verify_xp_save(save, 5)
        for rate in (1, 4.9, 10):
            with self.subTest(rate=rate), self.assertRaises(RuntimeError):
                smoke_profile.verify_xp_save(save, rate)

    def test_cook_save_needs_skill_xp_and_food(self):
        xp = [0] * 25
        xp[8], xp[11], xp[7] = 500, 800, 600
        save = {'experience': xp, 'inventories': {'inventory': [{'id': 'cooked_chicken'}]}}
        smoke_profile.verify_cook_save(save)
        burnt = {'experience': [0] * 8 + [500] + [0] * 2 + [400] + [0] * 13, 'inventories': {'inventory': [{'id': 'burnt_chicken'}]}}
        smoke_profile.verify_cook_save(burnt)
        for broken in ({'experience': [0] * 25, 'inventories': save['inventories']},
                       {'experience': xp, 'inventories': {'inventory': []}}):
            with self.subTest(broken=broken), self.assertRaises(RuntimeError):
                smoke_profile.verify_cook_save(broken)

    def test_shop_save_needs_coins_and_no_sold_item(self):
        smoke_profile.verify_shop_save({'inventories': {'inventory': [{'id': 'coins', 'amount': 4}]}})
        for items in ([], [{'id': 'coins', 'amount': 4}, {'id': 'bronze_dagger'}]):
            with self.subTest(items=items), self.assertRaises(RuntimeError):
                smoke_profile.verify_shop_save({'inventories': {'inventory': items}})

    def test_strict_shop_save_needs_the_purchased_item(self):
        smoke_profile.verify_shop_save({'inventories': {'inventory': [{'id': 'coins', 'amount': 2}, {'id': 'cake_tin'}]}}, 'Cake tin')
        with self.assertRaises(RuntimeError):
            smoke_profile.verify_shop_save({'inventories': {'inventory': [{'id': 'coins', 'amount': 2}]}}, 'Cake tin')

    def test_druidic_save(self):
        xp = [0] * 15 + [2500] + [0] * 9
        smoke_profile.verify_druidic_save({'variables': {'druidic_ritual': 'completed', 'quest_points': 4}, 'experience': xp})
        with self.assertRaises(RuntimeError):
            smoke_profile.verify_druidic_save({'variables': {'druidic_ritual': 'kaqemeex', 'quest_points': 0}, 'experience': xp})


if __name__ == '__main__':
    unittest.main()
