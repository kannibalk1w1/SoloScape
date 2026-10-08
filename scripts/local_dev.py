"""Local source-build launcher. Own only the child processes created here."""
import fcntl
import errno
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "upstream/game-server"
CLIENT = ROOT / "upstream/runelite-client"
RUNTIME = ROOT / ".runtime"
PORT = 43594
READY_TIMEOUT = 180
PINNED = {
    "game-server": "9f9113559eb686abd917893b5dca16404be07f93",
    "634-client": "b39d45f49a0480f3f200fe3e31ad0798faf163ab",
    "runelite-client": "297bc8a4861755b676855664d32859054779c067",
}


def java_version(executable):
    result = subprocess.run([executable, "-version"], capture_output=True, text=True)
    match = re.search(r'version "(?:1\.)?(\d+)', result.stdout + result.stderr)
    if result.returncode or not match:
        raise ValueError("could not parse java -version")
    return int(match.group(1))


def doctor():
    errors = []
    if shutil.which("flock") is None:
        errors.append("Install util-linux (flock) for safe client patch application.")
    for name, expected in PINNED.items():
        repo = ROOT / "upstream" / name
        if not (repo / ".git").is_dir():
            errors.append(f"Missing {repo}; clone https://github.com/2011Scape/{name}.git and checkout {expected}.")
            continue
        actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if actual != expected:
            errors.append(f"{name} is at {actual}; expected {expected}. Re-audit before updating pins.")
        for required in ("gradlew", "gradle/wrapper/gradle-wrapper.jar"):
            if not (repo / required).is_file():
                errors.append(f"Missing {repo / required}.")
    for variable, required in (("SERVER_JAVA", 21), ("CLIENT_JAVA", 8)):
        executable = os.environ.get(variable, "java")
        try:
            version = java_version(executable)
            if (variable == "SERVER_JAVA" and version < required) or (variable == "CLIENT_JAVA" and version != required):
                errors.append(f"{variable}: Java {version}; set {variable} to a JDK {required} executable.")
            else:
                print(f"OK {variable}: Java {version}")
            javac = Path(shutil.which(executable) or executable).resolve().with_name("javac")
            if not javac.is_file():
                errors.append(f"{variable} needs a JDK including javac, not only a JRE.")
        except (OSError, ValueError) as exc:
            errors.append(f"{variable}: {exc}. Install JDK {required} and set config/local.env.")
    for name in ("main_file_cache.dat2", "main_file_cache.idx255"):
        path = SERVER / "data/cache" / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Supply the compatible modified revision-634 cache: missing/empty {path}.")
    for name in ("clientlibs.jar", "graphics.jar", "trident-1.5.00.jar"):
        if not (CLIENT / "libs" / name).is_file():
            errors.append(f"Missing upstream client library {name}.")
    if (SERVER / "game.properties").exists():
        errors.append("External upstream/game-server/game.properties found. This launcher requires the audited internal defaults; move the override aside or audit it first.")
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        errors.append("No graphical display. Run from a Linux desktop session (Java 8 AWT needs X11/XWayland).")
    try:
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", PORT))
    except OSError as exc:
        if exc.errno in (errno.EPERM, errno.EACCES):
            errors.append(f"Port {PORT} probe denied by environment permissions; run doctor with local socket access.")
        else:
            errors.append(f"Port {PORT} is unavailable: {exc}. Stop the existing listener before launching.")
    print("NOTE: upstream binds all interfaces; restrict LAN access with your firewall for local development.")
    print("NOTE: cache presence checks do not prove revision/content compatibility.")
    print("Linux input nodes (not controller identification):", ", ".join(str(p) for p in Path("/dev/input").glob("event*")) or "none visible")
    for error in errors:
        print("ERROR:", error)
    print(f"Doctor: {len(errors)} error(s).")
    return not errors


def stop(process):
    if process is None or process.poll() is not None:
        return
    print(f"Stopping child {process.pid}; waiting for normal shutdown/save hooks.", flush=True)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    # Never SIGKILL a server whose save hooks may still be running.
    while process.poll() is None:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("Still waiting for shutdown; no forced kill. See .runtime logs.", flush=True)


def build(repo, java, task):
    env = os.environ.copy()
    env["JAVA_HOME"] = str(Path(shutil.which(java) or java).resolve().parent.parent)
    env["GRADLE_USER_HOME"] = str(ROOT / ".gradle")
    client_java = os.environ.get("CLIENT_JAVA", "java")
    client_jdk = Path(shutil.which(client_java) or client_java).resolve().parent.parent
    toolchains = f'-Dorg.gradle.java.installations.paths={env["JAVA_HOME"]},{client_jdk}'
    process = subprocess.Popen(["bash", "gradlew", "--no-daemon", toolchains, task], cwd=repo, env=env, start_new_session=True)
    try:
        if process.wait() != 0:
            raise RuntimeError(f"Build failed: {repo.name} {task}")
    finally:
        stop(process)


def jar(repo, pattern):
    files = list((repo / "build/libs").glob(pattern))
    if len(files) != 1:
        raise RuntimeError(f"Expected one {pattern} in {repo}/build/libs, found {len(files)}.")
    return files[0]


def launch(skip_build=False):
    RUNTIME.mkdir(exist_ok=True)
    with (RUNTIME / "launcher.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("A SoloScape launcher is already running.")
        if not doctor():
            return 1
        server_java = os.environ.get("SERVER_JAVA", "java")
        client_java = os.environ.get("CLIENT_JAVA", "java")
        if not skip_build:
            subprocess.run(["bash", str(ROOT / "scripts/apply-client-patches.sh")], check=True)
            build(SERVER, server_java, ":game:shadowJar")
            # Gradle 8 runs on JDK 21; upstream requests a separate Java 8 toolchain.
            build(CLIENT, server_java, ":client:shadowJar")
        server_jar = jar(SERVER / "game", "void-server-*.jar")
        client_jar = jar(CLIENT / "client", "void-client-*.jar")
        server = client = None
        offsets = {}

        def stream_logs():
            for name in ("server", "client"):
                path = RUNTIME / f"{name}.log"
                with path.open() as source:
                    source.seek(offsets.get(name, 0))
                    content = source.read()
                    offsets[name] = source.tell()
                for line in content.splitlines():
                    print(f"[{name}] {line}", flush=True)

        with (RUNTIME / "server.log").open("w") as server_log, (RUNTIME / "client.log").open("w") as client_log:
            try:
                server = subprocess.Popen([server_java, "-jar", str(server_jar)], cwd=SERVER, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + READY_TIMEOUT
                while True:
                    if server.poll() is not None:
                        raise RuntimeError("Server exited during startup; see .runtime/server.log.")
                    output = (RUNTIME / "server.log").read_text(errors="replace")
                    stream_logs()
                    # TCP binding happens BEFORE world/content/login readiness in Main.kt.
                    if re.search(r"Void loaded in \d+ms", output):
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError("Server readiness timed out; see .runtime/server.log.")
                    time.sleep(0.25)
                client = subprocess.Popen([client_java, "-jar", str(client_jar), "--address", "127.0.0.1", "--port", str(PORT)], cwd=CLIENT, stdout=client_log, stderr=subprocess.STDOUT, start_new_session=True)
                print("Client started on localhost. Logs: .runtime/server.log and .runtime/client.log. Ctrl+C stops both.", flush=True)
                while client.poll() is None:
                    stream_logs()
                    if server.poll() is not None:
                        raise RuntimeError("Server exited; see .runtime/server.log.")
                    time.sleep(0.25)
                return client.returncode
            finally:
                # Make cleanup resistant to a second Ctrl+C during saving.
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                stop(client)
                stop(server)
                stream_logs()


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if sys.argv[1:] == ["doctor"]:
            sys.exit(0 if doctor() else 1)
        elif sys.argv[1:] in (["run"], ["run", "--no-build"]):
            sys.exit(launch("--no-build" in sys.argv))
        else:
            sys.exit("Usage: local_dev.py doctor | run [--no-build]")
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit(f"ERROR: {exc}")
