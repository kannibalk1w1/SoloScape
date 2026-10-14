import os
import argparse
import selectors
from pathlib import Path
import subprocess
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_dev, profile_session, profiles
from unittest.mock import patch
import signal
import json
from native_metrics import NativeMetrics
from summarise_frame_trace import summarise as summarise_frames

def verify_content_save(saved):
    expected = {'imp_catcher': 'completed', 'blood_pact': 'started', 'druidic_ritual': 'completed'}
    variables = saved.get('variables', {})
    if any(variables.get(key) != value for key, value in expected.items()):
        raise RuntimeError('Content quest progress was not preserved in the native save/reload.')
    experience = saved.get('experience', [])
    # Native saves use tenths of XP; Skill ordinal 15 is Herblore. Imp Catcher grants 1 QP; Druidic Ritual grants 4.
    if len(experience) <= 15 or experience[15] != 2500 or variables.get('quest_points') != 5:
        raise RuntimeError('Druidic Ritual XP/quest-point rewards were not preserved.')


def verify_blood_pact_save(saved, *, kill_cultists=False, kayle=None, caitlin=None, magic=False):
    """Earned Blood Pact progress must survive Save & Quit and Continue."""
    variables = saved.get('variables', {})
    fates = {'kill': 'killed', 'spare': 'spared'}
    default = 'killed' if kill_cultists else 'spared'
    expected = {'blood_pact': 'completed', 'blood_pact_kayle': fates.get(kayle, default), 'blood_pact_caitlin': fates.get(caitlin, default), 'blood_pact_reese': 'killed', 'quest_points': 1}
    wrong = {key: variables.get(key) for key, value in expected.items() if variables.get(key) != value}
    if wrong:
        raise RuntimeError(f'Blood Pact progress was not preserved: {wrong}')
    carried = {item.get('id') for items in saved.get('inventories', {}).values() for item in items if item}
    missing = {'kayles_sling', 'caitlins_staff', 'reeses_sword', 'bronze_sword'} - carried
    if missing:
        raise RuntimeError(f'Blood Pact loot or wielded sword missing after reload: {sorted(missing)}')
    experience = saved.get('experience', [])
    # Tenths of XP; ordinals Attack 0, Defence 1, Strength 2, Ranged 4, Magic 6 each receive 100 quest XP.
    if len(experience) < 7 or any(experience[skill] < 1000 for skill in (0, 1, 2, 4, 6)):
        raise RuntimeError('Blood Pact XP rewards were not preserved.')
    if magic:
        equipment = saved.get('inventories', {}).get('worn_equipment', [])
        if 'caitlins_staff' not in {item.get('id') for item in equipment if item}:
            raise RuntimeError('Caitlin\'s staff is not wielded after reload.')
        # Magic XP above the 100 XP quest reward (tenths of XP) came from real spell casts.
        runes = {item.get('id'): item.get('amount', 1) for item in saved.get('inventories', {}).get('inventory', []) if item}
        print('Saved runes after the staff fight: air', runes.get('air_rune', 0), 'mind', runes.get('mind_rune', 0), '(started with 25 and 15)')
        if runes.get('mind_rune', 0) >= 15:
            raise RuntimeError('Starter mind runes were not spent by casting.')
        if experience[6] <= 1000:
            raise RuntimeError(f'Magic XP {experience[6]} shows no casting beyond the quest reward.')


def verify_druidic_save(saved):
    """Earned Druidic Ritual must survive Save & Quit and Continue."""
    variables = saved.get('variables', {})
    if variables.get('druidic_ritual') != 'completed' or variables.get('quest_points') != 4:
        raise RuntimeError(f"Druidic Ritual progress was not preserved: {variables.get('druidic_ritual')}, QP {variables.get('quest_points')}")
    experience = saved.get('experience', [])
    # Tenths of XP; Herblore (ordinal 15) is rewarded 250 XP and nothing else grants it.
    if len(experience) <= 15 or experience[15] != 2500:
        raise RuntimeError('Druidic Ritual Herblore reward was not preserved.')


def verify_cook_save(saved):
    """Woodcutting, Firemaking and Cooking XP and the cooked food must survive Save & Quit and Continue."""
    experience = saved.get('experience', [])
    # Tenths of XP; Cooking 7, Woodcutting 8, Firemaking 11.
    if len(experience) <= 11 or experience[8] <= 0 or experience[11] <= 0:
        raise RuntimeError('Woodcutting or Firemaking XP was not saved.')
    items = {}
    for stack in saved.get('inventories', {}).get('inventory', []):
        if stack:
            items[stack.get('id')] = items.get(stack.get('id'), 0) + stack.get('amount', 1)
    if not (items.get('cooked_chicken') or items.get('burnt_chicken')) or experience[7] <= 0 and not items.get('burnt_chicken'):
        raise RuntimeError(f'Cooked food or Cooking XP missing after reload: {items} cooking xp {experience[7]}')


def verify_xp_save(saved, rate):
    """Two normal-tree logs are 25 XP each; the world's rate must scale that exactly and the saved value must survive Continue."""
    experience = saved.get('experience', [])
    expected = round(2 * 25 * rate * 10)
    if len(experience) <= 8 or experience[8] != expected:
        raise RuntimeError(f'Woodcutting XP {experience[8] if len(experience) > 8 else None} (tenths) is not the {expected} expected at rate {rate}.')


def verify_shop_save(saved, bought=None):
    """The sale's coins and the purchased item must survive Save & Quit and Continue; the sold dagger must be gone.

    A strict purchase acceptance names the bought item (display name). It must not be an item the starter kit
    already holds, and a probe that could not buy (`buy_blocked`) is never a pass.
    """
    items = {}
    for stack in saved.get('inventories', {}).get('inventory', []):
        if stack:
            items[stack.get('id')] = items.get(stack.get('id'), 0) + stack.get('amount', 1)
    if items.get('coins', 0) <= 0:
        raise RuntimeError(f'No coins left after the shop round trip: {items}')
    if 'bronze_dagger' in items:
        raise RuntimeError('The sold bronze dagger is still in the saved inventory.')
    if bought is not None:
        item = bought.strip().lower().replace(' ', '_')
        if items.get(item, 0) < 1:
            raise RuntimeError(f'The purchased {bought} is missing from the saved inventory: {items}')


def _main():
    parser=argparse.ArgumentParser(description="Disposable native New/Continue/save and optional adventure UI probe.")
    parser.add_argument("--adventure",action="store_true",help="Probe real native adventure tabs, local settings and software overlay intervals.")
    parser.add_argument("--journey",action="store_true",help="Actual Lumbridge kitchen/bank round trip, Withdraw-X cancellation and bank search in disposable worlds.")
    parser.add_argument("--text",action="store_true",help="Focused native text fixture plus logout/relog/save checks; skips adventure-tab/performance stages.")
    parser.add_argument("--desktop",action="store_true",help="Use the explicitly authorized current X11/XWayland display; never stop that display.")
    parser.add_argument("--sidebar",action="store_true",help="Stress native RuneLite sidebar resizing, Configuration and keyboard toggles; check fresh controller startup.")
    parser.add_argument("--sidebar-baseline",action="store_true",help="Reproduce sidebar resizing against an older build without active hotkeys or controller defaults.")
    parser.add_argument("--performance",action="store_true",help="Compare controller overhead and reduced scene rendering in a disposable stationary scene.")
    parser.add_argument("--fullscreen-gl-only",action="store_true",help="Check fullscreen from focused OpenGL gameplay rather than the initial software window.")
    parser.add_argument("--fullscreen",action="store_true",help="Exercise the registered F11 fullscreen key with real software and OpenGL renderers and restore window bounds.")
    parser.add_argument("--playtest-two",action="store_true",help="Check player-lit fire cooking and Blood Pact instance projection in a disposable admin fixture.")
    parser.add_argument("--map",action="store_true",help="Open and close the real world map through native controller gateways.")
    parser.add_argument("--content-coverage",action="store_true",help="Native quest intro/reward and production fixtures with supplied materials; no actual-route claim.")
    parser.add_argument("--blood-pact",action="store_true",help="Play The Blood Pact from a fresh character with controller input only: real travel, earned combat, loot and B cancellation; no admin fixtures.")
    parser.add_argument("--druidic-ritual",action="store_true",help="Earn Druidic Ritual from a fresh character: hunt the four meats, walk to Taverley by stick, perform the ritual; no admin fixtures.")
    parser.add_argument("--gather-cook",action="store_true",help="Earn logs, a player-lit fire and cooked chicken through controller item-use, with a B cancellation of the cooking menu; no admin fixtures.")
    parser.add_argument("--world-xp-check",type=float,default=0,help="Earn two logs in a disposable world configured with this XP rate (and optional --world-drops/--world-infinite-run), then verify the exactly scaled Woodcutting XP survives Continue.")
    parser.add_argument("--world-drops",type=float,default=1)
    parser.add_argument("--world-infinite-run",action="store_true")
    parser.add_argument("--deck-route-software",action="store_true",help="With --deck-route-seconds: run the real-map route on the software renderer (private Xvfb cannot start the OpenGL toolkit). Host evidence only.")
    parser.add_argument("--shop-trade",action="store_true",help="Earn coins by selling a starter item to the Lumbridge general store and buy another item back through the native shop panel; no admin fixtures.")
    parser.add_argument("--druidic-dev-stage",type=int,default=0,help="Debug only: start the Druidic probe at a later stage using admin teleports/items. Results are labelled as a fixture, never earned acceptance.")
    parser.add_argument("--blood-pact-magic",action="store_true",help="Earned Blood Pact where Reese is beaten with Caitlin's staff and an autocast spell using tutor runes; implies --blood-pact.")
    parser.add_argument("--blood-pact-kayle",choices=("spare","kill"),help="Override Kayle's fate in the earned Blood Pact route; implies --blood-pact.")
    parser.add_argument("--blood-pact-caitlin",choices=("spare","kill"),help="Override Caitlin's fate in the earned Blood Pact route; implies --blood-pact.")
    parser.add_argument("--blood-pact-reese",choices=("kill","spare"),default="kill",help="Reese's final dialogue choice (he dies either way); implies --blood-pact when spare.")
    parser.add_argument("--blood-pact-kill-cultists",action="store_true",help="Run the earned Blood Pact route choosing to kill Kayle and Caitlin; implies --blood-pact.")
    parser.add_argument("--save-quit",action="store_true",help="Confirm the in-game Save & Quit gateway and verify normal server save/shutdown.")
    parser.add_argument("--artwork",action="store_true",help="Capture actual native cache item sprites for UI previews in a disposable world.")
    parser.add_argument("--tab-bar",action="store_true",help="Drive D-pad tab-bar focus through the plugin input tick: order, highlight, A ownership, opening and B to world.")
    parser.add_argument("--deck60",action="store_true",help="Full-resolution alternating pacing/controller/OpenGL comparisons in disposable worlds.")
    parser.add_argument("--deck60-gl-only",action="store_true",help="Skip software stages and compare OpenGL pacing at full resolution.")
    parser.add_argument("--deck-route-seconds",type=int,default=0,help="Repeat the real-map full-resolution route for 60–3600 seconds, then verify a no-action reload.")
    options=parser.parse_args()
    if options.druidic_ritual or options.gather_cook or options.world_xp_check or options.shop_trade:options.blood_pact=True
    if options.blood_pact_kill_cultists or options.blood_pact_magic or options.blood_pact_kayle or options.blood_pact_caitlin or options.blood_pact_reese=="spare":options.blood_pact=True
    if options.fullscreen_gl_only:options.fullscreen=True
    if options.deck60_gl_only:options.deck60=True
    if options.deck_route_seconds and not 60<=options.deck_route_seconds<=3600:parser.error('Route duration must be 60–3600 seconds.')
    if options.deck_route_seconds and (options.deck60 or options.adventure or options.journey or options.text or options.map or options.tab_bar or options.fullscreen):parser.error('Run the sustained route separately from other probes.')
    if options.sidebar_baseline:options.sidebar=True
    if options.text or options.journey:options.adventure=True
    signal.signal(signal.SIGTERM, local_dev.interrupted)
    root=local_dev.ROOT;testroot=root/'.runtime/alpha-tests'/('session-'+str(time.time_ns()));testroot.mkdir(parents=True,exist_ok=True)
    profiles.PROFILES=testroot/'profiles'
    profile=profiles.create('Native isolated smoke','AlphaTest')
    if options.world_xp_check:
        profiles.configure_world(profile.manifest['id'],{'xp':options.world_xp_check,'drops':options.world_drops,'infinite_run':options.world_infinite_run})
    marker=testroot/'native-login.marker';marker.unlink(missing_ok=True)
    original=subprocess.Popen
    def fingerprint():
        result={}
        for name in ('data/saves','data/errors','data/.temp'):
            base=local_dev.SERVER/name
            for path in base.rglob('*'):
                if path.is_file():
                    st=path.stat();result[str(path)]=(st.st_size,st.st_mtime_ns)
        return result
    before=fingerprint()
    savebefore=None
    harness=root/'.runtime/alpha-tests/harness'
    harness.mkdir(parents=True,exist_ok=True)
    clientjar=local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar')
    javac=Path(os.environ['CLIENT_JAVA']).with_name('javac')
    subprocess.run([str(javac),'-cp',str(clientjar),'-d',str(harness),str(root/'scripts/harness/NativeSessionSmoke.java'),str(root/'scripts/harness/NativeAdventureProbe.java'),str(root/'scripts/harness/NativeTextProbe.java'),str(root/'scripts/harness/NativePlayableLoopProbe.java'),str(root/'scripts/harness/NativeSidebarProbe.java'),str(root/'scripts/harness/NativePerformanceProbe.java'),str(root/'scripts/harness/NativeMapProbe.java'),str(root/'scripts/harness/NativeTabBarProbe.java'),str(root/'scripts/harness/NativeArtworkProbe.java'),str(root/'scripts/harness/NativeQuitProbe.java'),str(root/'scripts/harness/NativeContentCoverageProbe.java'),str(root/'scripts/harness/NativeBloodPactProbe.java'),str(root/'scripts/harness/NativePlaytestTwoProbe.java'),str(root/'scripts/harness/NativeFullscreenProbe.java'),str(root/'scripts/harness/NativeDeck60Probe.java'),str(root/'scripts/harness/NativeDeckRouteProbe.java')],check=True)
    x=None
    if options.desktop:
        if not os.environ.get('DISPLAY'):
            raise RuntimeError('--desktop requires an explicit DISPLAY and working X11 authorization.')
    else:
        read_display,write_display=os.pipe()
        x=original(['Xvfb','-displayfd',str(write_display),'-screen','0','1280x800x24','-nolisten','tcp'],pass_fds=(write_display,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        os.close(write_display)
    try:
        if x is not None:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(read_display,selectors.EVENT_READ)
                    if not selector.select(10):raise RuntimeError('Private Xvfb display handshake timed out.')
                display_number=os.read(read_display,128).decode('ascii').strip()
                if not display_number.isdigit() or x.poll() is not None:raise RuntimeError('Private Xvfb failed to allocate its own display.')
                os.environ['DISPLAY']=':'+display_number
            finally:os.close(read_display)
        def popen(argv,**kwargs):
            if '-jar' in argv and any('void-client-' in arg for arg in argv):
                i=argv.index('-jar');jar=argv[i+1]
                label='Existing authorized X11/XWayland desktop; native overlay-render intervals, real Gateway/synthetic UI input and AWT events through native canvas mouse handlers. No physical controller or Gaming Mode acceptance.' if options.desktop else 'Private owned Xvfb/software rendering; native overlay-render intervals, real Gateway/synthetic UI input and native Robot mouse logout. No GPU/Deck/controller acceptance.'
                argv=argv[:i]+['-Dsoloscape.probe.environment='+label]+(['-Dsoloscape.probe.awt.mouse=true'] if options.desktop else [])+(['-Dsoloscape.adventure.probe=true'] if options.adventure else [])+(['-Dsoloscape.text.probe.fast=true'] if options.text else [])+(['-Dsoloscape.playable.probe=true'] if options.journey else [])+(['-Dsoloscape.deck60.route=true','-Dsoloscape.deck60.route.seconds='+str(options.deck_route_seconds if iteration==0 else 0),'-Dsoloscape.performance.timings=true']+(['-Dsoloscape.deck60.route.software=true'] if options.deck_route_software else []) if options.deck_route_seconds else [])+(['-Dsoloscape.deck60.startStage=5'] if options.deck60_gl_only else [])+(['-Dsoloscape.deck60.probe=true','-Dsoloscape.performance.timings=true'] if options.deck60 else [])+(['-Dsoloscape.fullscreen.glOnly=true'] if options.fullscreen_gl_only else [])+(['-Dsoloscape.fullscreen.probe=true']+([] if options.desktop else ['-Dsoloscape.fullscreen.softwareOnly=true']) if options.fullscreen else [])+(['-Dsoloscape.playtest2.probe=true'] if options.playtest_two and iteration==0 else [])+(['-Dsoloscape.map.probe=true'] if options.map else [])+(['-Dsoloscape.content.probe=true'] if options.content_coverage and iteration==0 else [])+(['-Dsoloscape.bloodpact.probe=true'] + (['-Dsoloscape.bloodpact.route=druidic','-Dsoloscape.probe.seconds=7200']+(['-Dsoloscape.druidic.devStage='+str(options.druidic_dev_stage)] if options.druidic_dev_stage else []) if options.druidic_ritual else []) + (['-Dsoloscape.bloodpact.route=cook','-Dsoloscape.probe.seconds=1800'] if options.gather_cook else [])+(['-Dsoloscape.bloodpact.route=xp','-Dsoloscape.probe.seconds=1800'] if options.world_xp_check else [])+(['-Dsoloscape.bloodpact.route=shop','-Dsoloscape.probe.seconds=900'] if options.shop_trade else [])+(['-Dsoloscape.bloodpact.killCultists=true'] if options.blood_pact_kill_cultists else []) + (['-Dsoloscape.bloodpact.magic=true'] if options.blood_pact_magic else []) + (['-Dsoloscape.bloodpact.kayle='+options.blood_pact_kayle] if options.blood_pact_kayle else []) + (['-Dsoloscape.bloodpact.caitlin='+options.blood_pact_caitlin] if options.blood_pact_caitlin else []) + (['-Dsoloscape.bloodpact.reese='+options.blood_pact_reese] if options.blood_pact_reese=="spare" else []) if options.blood_pact and iteration==0 else [])+(['-Dsoloscape.quit.probe=true'] if options.save_quit and iteration==0 else [])+(['-Dsoloscape.artwork.probe=true'] if options.artwork and iteration==0 else [])+(['-Dsoloscape.tabbar.probe=true'] if options.tab_bar and iteration==0 else [])+(['-Dsoloscape.performance.probe=true'] if options.performance else [])+(['-Dsoloscape.sidebar.probe=true'] if options.sidebar else [])+(['-Dsoloscape.sidebar.baseline=true'] if options.sidebar_baseline else [])+['-cp',jar+':'+str(harness),'NativeSessionSmoke',str(marker),'43595']
            if (options.deck60 or options.deck_route_seconds) and any("void-server-" in arg for arg in argv):
                argv=argv[:1]+["-Dsoloscape.performance.timings.file="+str(testroot/("server-new.csv" if iteration==0 else "server-continue.csv"))]+argv[1:]
            if options.journey and any("void-server-" in arg for arg in argv):
                kwargs["env"]=dict(kwargs.get("env") or os.environ,SOLOSCAPE_NATIVE_PROBE="1")
            if (options.playtest_two or options.content_coverage or options.druidic_dev_stage) and any("void-server-" in arg for arg in argv):
                kwargs["env"]=dict(kwargs.get("env") or os.environ,**{'development.admin.name':'AlphaTest'})
            process=original(argv,**kwargs)
            if any('void-server-' in arg for arg in argv):metrics.add(process,'server')
            elif any('void-client-' in arg for arg in argv):metrics.add(process,'client')
            return process
        elapsed=[];adventure=[];observations=[]
        for iteration in range(2):
            if x is not None and x.poll() is not None:raise RuntimeError('Owned private display exited; refusing another display.')
            session_started=time.monotonic()
            marker.unlink(missing_ok=True)
            metrics=NativeMetrics();metrics.start()
            try:
                with patch.object(subprocess,'Popen',side_effect=popen):
                    def notify(stage,message):
                        metrics.stage(stage)
                        print(stage,message,flush=True)
                    code=profile_session.run(profile,threading.Event(),notify,port=43595)
            finally:
                observation=metrics.finish();observations.append(observation)
                (testroot/('resources-new.json' if iteration==0 else 'resources-continue.json')).write_text(json.dumps(observation,indent=2)+'\n')
            elapsed.append(round(time.monotonic()-session_started,3))
            if code or not marker.exists() or not profile.metadata()['saved']:
                raise RuntimeError('Native smoke failed; inspect this disposable profile’s logs.')
            if options.deck_route_seconds:
                for suffix in ('json','csv'):
                    Path(str(marker)+'.route.'+suffix).replace(testroot/('route-new.'+suffix if iteration==0 else 'route-continue.'+suffix))
                import csv
                name='route-new' if iteration==0 else 'route-continue'
                with (testroot/(name+'.csv')).open(newline='') as source:
                    frame_summary=summarise_frames(csv.DictReader(source))
                (testroot/(name+'-frames.json')).write_text(json.dumps(frame_summary,indent=2)+'\n')
            if options.deck60:
                for suffix in ('json','csv'):
                    Path(str(marker)+'.deck60.'+suffix).replace(testroot/('deck60-new.'+suffix if iteration==0 else 'deck60-continue.'+suffix))
            if options.tab_bar and iteration==0 and not Path(str(marker)+'.tab-bar.json').is_file():
                raise RuntimeError('Tab-bar probe did not record a result.')
            if options.adventure:
                adventure.append(json.loads(Path(str(marker)+'.adventure.json').read_text()))
                Path(str(marker)+'.adventure.json').replace(testroot/('adventure-new.json' if iteration==0 else 'adventure-continue.json'))
            saved=profiles.validate_save((profile.state/'saves/alphatest.toml').read_bytes())
            if options.content_coverage:
                verify_content_save(saved)
            if options.shop_trade:
                shop_result=json.loads((Path(str(marker)+'.bloodpact.json') if iteration==0 else testroot/'shop.json').read_text())
                if 'buy_blocked' in shop_result or not shop_result.get('bought'):
                    raise RuntimeError(f"Shop purchase was not completed: {shop_result.get('buy_blocked', 'no purchase recorded')}")
                verify_shop_save(saved, shop_result['bought'])
                if iteration==0:
                    Path(str(marker)+'.bloodpact.json').replace(testroot/'shop.json')
            elif options.world_xp_check:
                verify_xp_save(saved, options.world_xp_check)
                if iteration==0:
                    Path(str(marker)+'.bloodpact.json').replace(testroot/'xp-check.json')
            elif options.gather_cook:
                verify_cook_save(saved)
                if iteration==0:
                    Path(str(marker)+'.bloodpact.json').replace(testroot/'cook.json')
            elif options.druidic_ritual:
                verify_druidic_save(saved)
                if iteration==0:
                    Path(str(marker)+'.bloodpact.json').replace(testroot/'druidic.json')
            elif options.blood_pact:
                verify_blood_pact_save(saved, kill_cultists=options.blood_pact_kill_cultists, kayle=options.blood_pact_kayle, caitlin=options.blood_pact_caitlin, magic=options.blood_pact_magic)
                if iteration==0:
                    Path(str(marker)+'.bloodpact.json').replace(testroot/'blood-pact.json')
            if savebefore is not None:
                if not all(savebefore[k]==saved[k] for k in ('accountName','experience','inventories','tile')):
                    raise RuntimeError('Native save/reload changed a tested field.')
            savebefore=saved
        saveafter=profiles.validate_save((profile.state/'saves/alphatest.toml').read_bytes())
        print('Native save/reload fields preserved:',all(savebefore[k]==saveafter[k] for k in ('accountName','experience','inventories','tile')))
        print('Smoke client exit:',code)
        print('In-game marker:',marker.exists())
        print('Native character save:',profile.metadata()['saved'])
        print('Verified backups:',len(list((profile.directory/'backups').glob('*.zip'))))
        print('Original mutable paths unchanged:',before==fingerprint())
        if code or not marker.exists() or not profile.metadata()['saved'] or before!=fingerprint():raise RuntimeError('Native smoke failed; see private profile logs')
        # Cancel a real native startup while content is still loading. Compare the entire
        # saved world, including exchange files; never touch the legacy world.
        saved_world={str(p.relative_to(profile.state/'saves')):p.read_bytes() for p in (profile.state/'saves').rglob('*') if p.is_file()}
        cancelled=threading.Event()
        def cancel_loading():
            deadline=time.monotonic()+60
            log=profile.directory/'session-logs/server.log'
            while time.monotonic()<deadline:
                text=log.read_text(errors='replace') if log.exists() else ''
                # The current log is truncated before startup. Use cache/content loader output,
                # never the previous fully-ready log or a fixed delay.
                if ('MemoryCache' in text or 'DefinitionDecoder' in text) and 'Void loaded in' not in text:
                    cancelled.set();return
                time.sleep(.02)
            cancelled.set()
        observer=threading.Thread(target=cancel_loading)
        observer.start()
        try:
            code=profile_session.run(profile,cancelled,lambda stage,message:print(stage,message,flush=True),port=43595,client_enabled=False)
        finally:observer.join(65)
        log=(profile.directory/'session-logs/server.log').read_text(errors='replace')
        if 'Void loaded in' in log or not ('MemoryCache' in log or 'DefinitionDecoder' in log):
            raise RuntimeError('Native early cancellation was not observed; cannot claim this check.')
        after_cancel={str(p.relative_to(profile.state/'saves')):p.read_bytes() for p in (profile.state/'saves').rglob('*') if p.is_file()}
        if code or after_cancel!=saved_world or before!=fingerprint():raise RuntimeError('Cancelled native startup changed saved-world bytes.')
        print('Cancelled native startup preserved entire saved world:',after_cancel==saved_world)
        print('New/Continue complete-session seconds (includes client readiness and save):',elapsed)
        (testroot/'native-smoke-summary.json').write_text(json.dumps({'new_session_seconds':elapsed[0],'continue_session_seconds':elapsed[1],
            'native_startup_cancel_preserved':True,'original_mutable_paths_unchanged':before==fingerprint(),
            'session_environment':{key:os.environ.get(key) for key in ('XDG_SESSION_DESKTOP','XDG_CURRENT_DESKTOP','DISPLAY','SteamAppId','SteamGameId')},
            'adventure':adventure,'text_focused':options.text,'playable_journey':options.journey,'playtest_two':options.playtest_two,'fullscreen_probe':options.fullscreen,'fullscreen_renderers':'OpenGL only' if options.fullscreen_gl_only else 'software and OpenGL' if options.fullscreen and options.desktop else 'software only' if options.fullscreen else None,'sidebar_probe':options.sidebar,'sidebar_baseline':options.sidebar_baseline,'display':'existing-desktop' if options.desktop else 'private-xvfb',
            'precondition':'Desktop probes require hands off, awake display; real input/focus may interfere.' if options.desktop else 'Owned private display.',
            'screenshots':'Private evidence only; desktop overlays may appear or Wayland capture may be unavailable. Review before publishing.',
            'note':'Native session totals and overlay-render intervals; not physical controller or Gaming Mode acceptance.'},indent=2)+'\n')
        (testroot/'native-smoke-profile.txt').write_text(profile.manifest['id'])
    finally:
        if x is not None:
            x.terminate()
            try:x.wait(timeout=5)
            except subprocess.TimeoutExpired:
                x.kill();x.wait(timeout=5)  # Only this probe's owned display, never a game/save process.


def main():
    with local_dev.build_lock(shared=True):
        from deck_awake import keep_awake
        with keep_awake() as inhibition:
            print('Temporary display inhibition:', json.dumps(inhibition), flush=True)
            _main()


if __name__ == "__main__":
    main()
