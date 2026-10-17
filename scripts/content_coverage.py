#!/usr/bin/env python3
"""Run selected quest and production regressions against isolated native-server storage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET
import local_dev

SUITES = (
    'content.quest.free.blood_pact.BloodPactTest',
    'content.quest.free.imp_catcher.ImpCatcherTest',
    'content.quest.member.druidic_ritual.DruidicRitualTest',
    'content.skill.crafting.SpinningWheelTest',
    'content.skill.crafting.PotteryTest',
    'content.skill.smithing.SmithingTest',
    'content.skill.smithing.SmeltingTest',
    'content.skill.fletching.FletchingTest',
)

# Representative systems and shared contracts, not an exhaustive quest campaign.
M6_SUITES = (
    'content.skill.slayer.SlayerMasterTest',
    'content.skill.slayer.SlayerTaskTest',
    'content.skill.slayer.SlayerCombatFormulaTest',
    'content.skill.summoning.SummoningCraftingTest',
    'content.skill.summoning.SummoningLevelGateTest',
    'content.skill.summoning.FamiliarUtilitySpecialEffectTest',
    'content.skill.dungeoneering.DungeonGeneratorTest',
    'content.skill.dungeoneering.DungeonGenerationWorldTest',
    'content.area.wilderness.daemonheim.DungeoneeringPartyTest',
    'content.soloscape.ActualAdventureRouteTest',
    'content.soloscape.FullAdventureJourneyTest',
    'content.soloscape.SessionAdventureTest',
)


# Bounded acquisition and lifecycle contracts; not an earned Summoning journey.
SUMMONING_SUITES = (
    'content.area.asgarnia.taverley.PikkupstixTest',
    'content.skill.summoning.SummoningSupplyAcquisitionTest',
    'content.skill.summoning.SummoningLootDeliveryTest',
    'content.skill.summoning.ConnectedSpiritWolfSupplyTest',
    'content.skill.summoning.SoloSpiritWolfLifecycleTest',
    'content.skill.summoning.FamiliarOwnerIdentityTest',
    'content.skill.summoning.FamiliarDismissalIdentityTest',
    'content.skill.summoning.SummoningLevelGateTest',
    'content.skill.summoning.SummoningObeliskTest',
)


def read_results(report_directory, suites, archive):
    rows = []
    for suite in suites:
        path = report_directory / ('TEST-' + suite + '.xml')
        if not path.is_file():
            raise RuntimeError('Missing selected suite result: ' + suite)
        root = ET.parse(path).getroot()
        row = dict(suite=suite, **{key: int(root.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')})
        if row['tests'] < 1:
            raise RuntimeError('Selected suite ran no tests: ' + suite)
        (archive / path.name).write_bytes(path.read_bytes())
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('early', 'm6', 'journeys', 'summoning', 'capacity', 'dungeon', 'death', 'slayer', 'save', 'snapshot'), default='early')
    options = parser.parse_args()
    suites = {
        'snapshot': ('content.entity.player.SaveVariableSnapshotTest',),
        'save': (
            'world.gregs.voidps.engine.data.SaveQueueTest',
            'world.gregs.voidps.engine.data.PlayerSaveTest',
        ),
        'early': SUITES,
        'm6': M6_SUITES,
        'summoning': SUMMONING_SUITES,
        'slayer': (
            'content.skill.slayer.SlayerKillOwnershipTest',
            'content.skill.slayer.SlayerTaskTest',
            'content.skill.slayer.SlayerMasterTest',
        ),
        'death': (
            'content.entity.player.inv.TakeTest',
            'content.area.misthalin.lumbridge.church.DeathLootRecoveryTest',
            'content.area.misthalin.lumbridge.church.KeptItemChargePreservationTest',
            'content.area.misthalin.lumbridge.church.IdenticalItemsKeptOnDeathTest',
            'content.area.misthalin.lumbridge.church.GravestonesTest',
            'content.area.misthalin.lumbridge.church.GravestoneShopAuthorityTest',
            'content.area.misthalin.lumbridge.church.RepeatedGraveIdentityTest',
        ),
        'dungeon': (
            'content.skill.dungeoneering.DungeonRoomCoordinateTest',
            'content.skill.dungeoneering.DungeonGenerationWorldTest',
            'content.skill.dungeoneering.DungeonGeneratorTest',
            'content.skill.dungeoneering.SoloBossTrapdoorUnlockTest',
            'content.skill.dungeoneering.SoloDungeonRewardNoticeTest',
            'content.skill.dungeoneering.SoloDungeonLifecycleTest',
        ),
        'capacity': (
            'content.soloscape.ProductionCapacityRecoveryTest',
            'content.skill.fishing.FishingTest',
            'content.skill.cooking.CookingTest',
            'content.skill.cooking.CookingTargetLifetimeTest',
        ),
        'journeys': ('content.soloscape.FullAdventureJourneyTest',),
    }[options.group]
    directory = local_dev.RUNTIME / 'content-coverage' / str(time.time_ns())
    directory.mkdir(parents=True, mode=0o700)
    java = Path(os.environ.get('SERVER_JAVA', 'java'))
    if not java.is_absolute():
        import shutil
        java = Path(shutil.which(str(java)) or str(java))
    env = dict(os.environ, JAVA_HOME=str(java.resolve().parent.parent),
               GRADLE_USER_HOME=str(local_dev.ROOT / '.gradle'), SOLOSCAPE_TEST_ROOT=str(directory))
    module = 'engine' if options.group == 'save' else 'game'
    command = ['bash', 'gradlew', '--no-daemon', f':{module}:test']
    for suite in suites:
        command.extend(['--tests', suite])
    with local_dev.build_lock():
        report_directory = local_dev.SERVER / module / 'build/test-results/test'
        # Missing outputs force a fresh Gradle test run. Never attribute older XML
        # to a failed compilation or a suite which did not run this invocation.
        for suite in suites:
            (report_directory / ('TEST-' + suite + '.xml')).unlink(missing_ok=True)
        result = subprocess.run(command, cwd=local_dev.SERVER, env=env, check=False)
        rows = read_results(report_directory, suites, directory)
        patches = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted((local_dev.ROOT / 'patches/server').glob('*.patch'))}
    environment = ('Native engine unit and original disposable file-storage cases; no live world or physical acceptance.'
                   if options.group == 'save' else
                   'Isolated host native server; mixed unit, supplied-input and actual-map route fixtures. No graphical or physical controller acceptance. See suite sources for setup.')
    summary = {'environment': environment, 'module': module,
               'group': options.group, 'server_patches_sha256': patches,
               'suites': rows, 'exit_code': result.returncode}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('Coverage evidence:', directory / 'summary.json')
    if result.returncode or any(row['failures'] or row['errors'] or row['skipped'] for row in rows):
        raise RuntimeError('Selected coverage did not pass completely; inspect isolated evidence.')


if __name__ == '__main__':
    main()
