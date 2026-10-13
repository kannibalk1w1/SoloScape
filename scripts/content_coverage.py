#!/usr/bin/env python3
"""Run selected quest and production regressions against isolated native-server storage."""
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


def main():
    directory = local_dev.RUNTIME / 'content-coverage' / str(time.time_ns())
    directory.mkdir(parents=True, mode=0o700)
    java = Path(os.environ.get('SERVER_JAVA', 'java'))
    if not java.is_absolute():
        import shutil
        java = Path(shutil.which(str(java)) or str(java))
    env = dict(os.environ, JAVA_HOME=str(java.resolve().parent.parent),
               GRADLE_USER_HOME=str(local_dev.ROOT / '.gradle'), SOLOSCAPE_TEST_ROOT=str(directory))
    command = ['bash', 'gradlew', '--no-daemon', ':game:test']
    for suite in SUITES:
        command.extend(['--tests', suite])
    with local_dev.build_lock():
        result = subprocess.run(command, cwd=local_dev.SERVER, env=env, check=False)
        rows = []
        for suite in SUITES:
            path = local_dev.SERVER / 'game/build/test-results/test' / ('TEST-' + suite + '.xml')
            if not path.exists():
                raise RuntimeError('Missing selected suite result: ' + suite)
            root = ET.parse(path).getroot()
            rows.append(dict(suite=suite, **{key: int(root.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')}))
    summary = {'environment': 'Isolated native server; supplied inputs, teleport/combat fixtures in existing quest tests; no graphical or earned-route acceptance.',
               'suites': rows, 'exit_code': result.returncode}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('Coverage evidence:', directory / 'summary.json')
    if result.returncode or any(row['failures'] or row['errors'] or row['skipped'] for row in rows):
        raise RuntimeError('Selected coverage did not pass completely; inspect isolated evidence.')


if __name__ == '__main__':
    main()
