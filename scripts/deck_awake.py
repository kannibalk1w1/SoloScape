"""Temporary desktop idle inhibition; never changes power settings or unlocks a session."""
from contextlib import contextmanager


@contextmanager
def keep_awake():
    bus = interface = cookie = None
    status = {'inhibited': False, 'provider': 'org.freedesktop.ScreenSaver'}
    try:
        import dbus
        bus = dbus.SessionBus(private=True)
        interface = dbus.Interface(bus.get_object('org.freedesktop.ScreenSaver', '/ScreenSaver'), 'org.freedesktop.ScreenSaver')
        cookie = interface.Inhibit('SoloScape', 'Active local game session', timeout=5)
        status['inhibited'] = True
    except Exception as exc:
        # Optional outside a supported desktop (headless CI, a private Xvfb or
        # compositors with their own game-session inhibition).
        status['unavailable'] = type(exc).__name__
    try:
        yield status
    finally:
        if interface is not None and cookie is not None:
            try:
                interface.UnInhibit(cookie, timeout=5)
            except Exception:
                pass  # Closing our private connection also releases its inhibition.
        if bus is not None:
            try:
                bus.close()
            except Exception:
                pass
