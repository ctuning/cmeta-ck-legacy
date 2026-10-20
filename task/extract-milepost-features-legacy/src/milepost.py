"""Recovered MILEPOST GCC/ICI/XSB runtime and private extraction worker.

Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.
"""
import argparse
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

MAX_SOURCE = 65536
CAPSULES = {
    'milepost-runtime.tar.gz': 'e0e91e3963c9308a746667618500f3b63afeef668fd6c71a36577df76ed9bfb2',
    'compiler-support.tar.gz': '3bf0c3f8ba735d446e1b068bc19334cc786abdf17262ff5ceb45add34bc8e04f',
}


HEADERS_SHA256 = '587ffad6386f86d4cd0ce76cbd241f9c92e59eca17e7e8462e40642d32eb9f87'


def prepare_tools(root, capture):
    root.mkdir(parents=True, exist_ok=True)
    with (root/'prepare.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tools = root/'tools'
        if (tools/'ready.json').exists():
            if json.loads((tools/'ready.json').read_text()) != CAPSULES:
                raise ValueError('Installed software identity differs from the checked capsule')
            return tools
        stage = Path(tempfile.mkdtemp(prefix='install-', dir=root))
        try:
            for name, digest in CAPSULES.items():
                archive = capture/name
                with archive.open('rb') as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != digest:
                    raise ValueError('Software capsule checksum mismatch: '+name)
                with tarfile.open(archive) as tar:
                    tar.extractall(stage, filter='data')
            ccc = stage/'ccc-framework'
            # Relocate only the copied historical profiles, before making tools read-only.
            replacements = [
                (ccc/'cfg/ctuning/ccc-env.sh', '/home1/fursinne/fggwork/ccc-framework', str(tools/'ccc-framework')),
                (ccc/'cfg/ctuning/ccc-env.c.milepostgcc44', '/home1/fursinne/fggwork/compilers/ctuning-cc-2.5-gcc-4.4.4-ici-2.05-milepost-2.1/install', str(tools/'milepost')),
            ]
            for path, old, new in replacements:
                text = path.read_text()
                if old not in text:
                    raise ValueError('Unexpected historical profile: '+str(path))
                path.write_text(text.replace(old, new))
            (stage/'ready.json').write_text(json.dumps(CAPSULES, sort_keys=True))
            if tools.exists():
                raise ValueError('Incomplete software installation retained; inspect before retrying')
            stage.rename(tools)
            for parent, dirs, files in os.walk(tools):
                for name in files+dirs:
                    p = Path(parent)/name
                    if not p.is_symlink():
                        p.chmod(0o555 if p.is_dir() or p.stat().st_mode & 0o111 else 0o444)
            tools.chmod(0o555)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return tools


def prepare(root, capture):
    tools = prepare_tools(root, capture)
    headers = root/'headers'
    with (root/'prepare.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (headers/'ready.json').is_file():
            if json.loads((headers/'ready.json').read_text())['sha256'] != HEADERS_SHA256:
                raise ValueError('Installed C headers differ from the checked capsule')
            return tools
        archive = capture.parent/'20261020-headers/compiler-headers.tar.gz'
        with archive.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=HEADERS_SHA256:
                raise ValueError('C header capsule checksum mismatch')
        with tempfile.TemporaryDirectory(prefix='headers-',dir=root) as directory:
            stage = Path(directory)
            with tarfile.open(archive) as tar:
                tar.extractall(stage,filter='data')
            (stage/'headers/ready.json').write_text(json.dumps({'sha256':HEADERS_SHA256}))
            (stage/'headers').rename(headers)
        for parent,dirs,files in os.walk(headers):
            for name in files+dirs:
                path=Path(parent)/name
                if not path.is_symlink():path.chmod(0o555 if path.is_dir() else 0o444)
        headers.chmod(0o555)
    return tools


def job(root, source):
    if not isinstance(source, str) or not source.strip() or len(source.encode()) > MAX_SOURCE:
        return {'ok': False, 'error': 'Submit a nonempty C program of at most 64 KiB.'}
    tools = root/'tools'
    if not (tools/'ready.json').exists():
        return {'ok': False, 'error': 'The recovered compiler is not prepared.'}
    jobs = root/'jobs'
    jobs.mkdir(mode=0o700, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='extract-', dir=jobs) as directory:
        work = Path(directory)
        (work/'home').mkdir()
        for path in (tools/'ccc-framework/cfg/ctuning/application').iterdir():
            if path.is_file():
                shutil.copyfile(path, work/path.name)
        (work/'prog.c').write_text(source)
        (work/'_ccc_program_id').write_text('0\nctuning_legacy_program\n')
        env = {'PATH': str(tools/'support/bin')+':/usr/local/bin:/usr/bin:/bin',
               'HOME': str(work/'home'), 'TMPDIR': str(work), 'LANG': 'C', 'LC_ALL': 'C',
               'LD_LIBRARY_PATH': str(tools/'support/lib')+':'+str(tools/'milepost/lib'),
               'C_INCLUDE_PATH': str(root/'headers/usr/include')+':'+str(root/'headers/usr/include/x86_64-linux-gnu'),
               'XSB_DIR': str(tools/'milepost/3.2')}
        resource.setrlimit(resource.RLIMIT_CPU, (15, 17))
        resource.setrlimit(resource.RLIMIT_AS, (512<<20, 512<<20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8<<20, 8<<20))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        command = '. "$1"; export ICI_PROG_FEAT_PASS=fre CCC_ICI_FEATURES_STATIC_EXTRACT=1; ccc-comp milepostgcc44 -O1'
        with (work/'compiler.log').open('wb') as log:
            result = subprocess.run(['bash', '-c', command, 'milepost', str(tools/'ccc-framework/cfg/ctuning/ccc-env.sh')],
                                    cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        path = work/'ici_features_function.ft'
        text = path.read_text(errors='replace').strip() if path.exists() else ''
        fields = re.findall(r'\bft(\d+)=([-+0-9.eE]+)', text)
        valid = len(fields)==55 and {int(k) for k,v in fields}==set(range(1,56)) and all(math.isfinite(float(v)) for k,v in fields)
        record = {'ok': valid, 'gcc': '4.4.4', 'ici': '2.05', 'milepost': '2.1',
                  'ccc_returncode': result.returncode, 'wall_seconds': time.monotonic()-started,
                  'feature_count': len(fields) if valid else 0}
        if valid:
            record.update(features=text, values={'ft'+k: float(v) for k,v in fields})
        else:
            log = (work/'compiler.log').read_text(errors='replace')
            # Include source diagnostics, not the old framework's lengthy executable checks.
            diagnostics = [line for line in log.splitlines() if 'prog.c:' in line or 'error:' in line]
            record['error'] = 'Could not extract features. Check that the program is valid C89 (GNU89).'
            record['diagnostics'] = '\n'.join(diagnostics)[:2000]
        return record


def extract(root, source):
    root.mkdir(parents=True, exist_ok=True)
    with (root/'extract.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'ok': False, 'error': 'The legacy compiler is busy. Please try again shortly.'}
        return extract_locked(root, source)


def extract_locked(root, source):
    """Each compiler job gets a fresh process group, bounded lifetime and no inherited secrets."""
    start = time.monotonic()
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', '--root', str(root)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
    try:
        output, error = process.communicate(json.dumps({'source': source}).encode(), timeout=35)
        record = json.loads(output) if process.returncode==0 else {'ok': False, 'error': 'The compiler job could not complete.'}
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        record = {'ok': False, 'error': 'Feature extraction exceeded its time limit.'}
    except (ValueError, OSError):
        record = {'ok': False, 'error': 'The compiler job returned an invalid result.'}
    finally:
        # Reap any helpers left by the historical driver, including on successful jobs.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # A killed historical job cannot run TemporaryDirectory's cleanup itself.
        jobs = root/'jobs'
        if jobs.is_dir():
            for path in jobs.glob('extract-*'):
                if path.is_dir() and not path.is_symlink() and path.resolve().parent==jobs.resolve():
                    shutil.rmtree(path)
    record['wall_seconds'] = time.monotonic()-start
    return record


def serve(root, port):
    slots = threading.BoundedSemaphore(1)
    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, code, value):
            data = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            self.reply(200 if self.path=='/health' else 404, {'ready': (root/'tools/ready.json').exists() and (root/'headers/ready.json').exists(), 'service': 'milepost', 'runner_sha256': runner_sha256})
        def do_POST(self):
            if self.path!='/extract':
                return self.reply(404, {'ok': False, 'error': 'Unknown endpoint.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length<=0 or length>MAX_SOURCE*6+1024:
                    return self.reply(413, {'ok': False, 'error': 'Submit at most 64 KiB of C source.'})
                self.connection.settimeout(10)
                source = json.loads(self.rfile.read(length)).get('source')
                if not isinstance(source, str) or not source.strip() or len(source.encode())>MAX_SOURCE:
                    return self.reply(400, {'ok': False, 'error': 'Submit a nonempty C program of at most 64 KiB.'})
            except (ValueError, OSError, AttributeError):
                return self.reply(400, {'ok': False, 'error': 'Invalid extraction request.'})
            if not slots.acquire(False):
                return self.reply(429, {'ok': False, 'error': 'The legacy compiler is busy. Please try again shortly.'})
            try:
                result = extract(root, source)
                summary = {k: result.get(k) for k in ['ok', 'feature_count', 'wall_seconds', 'ccc_returncode']}
                summary.update(time=time.time(), source_sha256=hashlib.sha256(source.encode()).hexdigest())
                with (root/'requests.jsonl').open('a') as stream:
                    stream.write(json.dumps(summary)+'\n')
                self.reply(200 if result.get('ok') else 422, result)
            finally:
                slots.release()
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'serve', 'extract', 'job'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--port', type=int, default=8162)
    args = parser.parse_args()
    os.umask(0o077)
    if args.action=='prepare':
        prepare(args.root, args.capture)
        print(json.dumps({'ready': True}))
    elif args.action=='serve':
        serve(args.root, args.port)
    else:
        source = json.load(sys.stdin).get('source')
        print(json.dumps(job(args.root, source) if args.action=='job' else extract(args.root, source)))


if __name__=='__main__':
    main()
