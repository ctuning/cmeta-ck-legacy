"""Extract historical MILEPOST features: in a Linux container (default), natively on Linux or through a worker.

Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from task_c36be4b9314a45e0.api.ctask import InitCTask

SRC = Path(__file__).parent/'src'


class CTask(InitCTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module_file_path=__file__, **kwargs)

    def run(self, ctx, source_file: str='', output_file: str='', worker: str='',
            runtime_root: str='', endpoint: str='', capsules: str='',
            engine: str='', image: str='', volume: str=''):
        """Extract 55 static features from C89 source.

        The way is chosen in this order: --endpoint (a private HTTP service), --worker (a cMeta host),
        --runtime-root (native, Linux amd64), else a Linux container of --engine (docker or podman)
        started from --image, with the prepared runtime kept in the engine volume --volume.
        --capsules: a folder or URL (template with {name}) of the public capsules, default
        default_capsules of _desc.yaml; the runtime is prepared from them when it is not ready yet.
        Without --source-file the runtime is only prepared.
        """
        try:
            desc = getattr(self, 'cdesc', None) or {}
            runtime_root = runtime_root or os.environ.get('CMETA_MILEPOST_ROOT', '')
            capsules = capsules or os.environ.get('CMETA_MILEPOST_CAPSULES', '') or desc.get('default_capsules', '')
            source = None
            if source_file:
                source = Path(source_file).read_text(encoding='utf-8')
                if not source.strip() or len(source.encode())>65536:
                    return self.cm.error('Provide nonempty C source of at most 64 KiB')
            elif endpoint or worker:
                return self.cm.error('Provide --source-file=<C89 program>')
            request = json.dumps({'source': source})
            if endpoint:
                mode = 'endpoint'
                try:
                    response=urllib.request.urlopen(urllib.request.Request(endpoint,data=request.encode(),
                        headers={'Content-Type':'application/json'}),timeout=40)
                except urllib.error.HTTPError as error:
                    response=error
                with response:
                    result=json.load(response)
            elif worker:
                mode = 'worker'
                r = self._worker(worker, request)
                if r['return']:
                    return r
                result = r['result']
            elif runtime_root:
                mode = 'native'
                if sys.platform!='linux':
                    return self.cm.error('Direct extraction requires Linux amd64; leave out --runtime-root to run it in a Linux container')
                root = Path(runtime_root)
                if capsules and not ((root/'tools/ready.json').is_file() and (root/'headers/ready.json').is_file()):
                    print('cMeta info: preparing the MILEPOST runtime in '+str(root)+' from '+capsules)
                    process = subprocess.run([sys.executable, str(SRC/'milepost.py'), 'prepare', '--root', str(root),
                                              '--capsules', capsules], stdin=subprocess.DEVNULL, capture_output=True, timeout=3600)
                    if process.returncode:
                        return self.cm.error('Preparing the runtime failed: '+process.stderr.decode(errors='replace')[-2000:])
                if source is None:
                    return {'return': 0, 'mode': mode, 'prepared': str(root)}
                process = subprocess.run([sys.executable, str(SRC/'milepost.py'), 'extract', '--root', runtime_root],
                                         input=request.encode(), capture_output=True, timeout=45)
                if process.returncode:
                    return self.cm.error('Native extraction failed: '+process.stderr.decode(errors='replace')[-2000:])
                result = json.loads(process.stdout)
            else:
                mode = 'container'
                r = self._container(capsules, request if source is not None else None,
                                    engine or desc.get('container_engine', 'docker'),
                                    image or desc.get('container_image', 'python:3.12-slim'),
                                    volume or desc.get('container_volume', 'cmeta-milepost-legacy-20261114'))
                if r['return'] or source is None:
                    return r
                result = r['result']
            if output_file:
                written = self.cm.utils.files.safe_write_file(output_file, result, atomic=True)
                if self.cm.catch_error(written):
                    return written
            if not result.get('ok'):
                return {'return': 1, 'error': result.get('error', 'Feature extraction failed'), 'extraction': result}
            print(result['features'])
            return {'return': 0, 'mode': mode, 'extraction': result}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            return self.cm.error(str(error))

    def _container(self, capsules, request, engine, image, volume):
        """Prepare the runtime in the engine volume (once; a quick check afterwards), then extract with the
        volume read-only, no network, no capabilities and an unprivileged user. Paths never cross: the source
        goes in on stdin and the result comes back on stdout."""
        exe = shutil.which(engine)
        if not exe:
            return self.cm.error(f'"{engine}" is not installed here (cx tool setup {engine} --install); '
                                 'on Linux amd64 --runtime-root=<folder> runs the compiler natively')
        if not capsules:
            return self.cm.error('Give --capsules=<folder or URL of the MILEPOST capsules> '
                                 '(default_capsules is not set in _desc.yaml yet)')
        run = [exe, 'run', '--rm', '--platform', 'linux/amd64', '-v', f'{SRC}:/milepost-src:ro']
        prepare = run + ['-v', f'{volume}:/runtime']
        if '://' in capsules:
            where = capsules
        else:
            folder = Path(capsules).resolve()
            if not folder.is_dir():
                return self.cm.error(f'--capsules: no folder {folder}')
            prepare += ['-v', f'{folder}:/capsules:ro']
            where = '/capsules'
        known = subprocess.run([exe, 'volume', 'inspect', volume], stdin=subprocess.DEVNULL, capture_output=True)
        if known.returncode:
            print(f'cMeta info: preparing the MILEPOST runtime in the {engine} volume {volume} from {capsules} '
                  '(once; about 400 MB)')
        process = subprocess.run(prepare + [image, 'python3', '/milepost-src/milepost.py', 'prepare',
                                            '--root', '/runtime', '--capsules', where],
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=3600)
        if process.returncode:
            return self.cm.error('Preparing the runtime in the container failed: '
                                 + process.stderr.decode(errors='replace')[-2000:])
        if request is None:
            return {'return': 0, 'mode': 'container', 'prepared': volume, 'engine': engine, 'image': image}
        process = subprocess.run(run + ['-i', '--network', 'none', '--cap-drop', 'ALL',
                                        '--security-opt', 'no-new-privileges', '--pids-limit', '512',
                                        '--memory', '2g', '--user', '65534:65534', '-v', f'{volume}:/runtime:ro',
                                        image, 'python3', '/milepost-src/milepost.py', 'extract',
                                        '--root', '/runtime', '--work', '/tmp/milepost-work'],
                                 input=request.encode(), capture_output=True, timeout=300)
        if process.returncode:
            return self.cm.error('Extraction in the container failed: '+process.stderr.decode(errors='replace')[-2000:])
        return {'return': 0, 'result': json.loads(process.stdout)}

    def _worker(self, worker, request):
        script = "python3 - <<'CMETA_MILEPOST_REQUEST'\nimport json,urllib.request,urllib.error\n"
        script += 'data='+repr(request.encode())+'\n'
        script += "try:\n r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8162/extract',data=data,headers={'Content-Type':'application/json'}),timeout=40)\nexcept urllib.error.HTTPError as e:\n r=e\nprint(r.read().decode())\nCMETA_MILEPOST_REQUEST\n"
        session = os.environ.get('CMETA_TEST_SESSION')
        directory = Path.home()/'cmeta-tests'/session if session else Path(self.cm.home_path)/'repos/local/tmp/milepost-client'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', dir=directory,
                                         encoding='utf-8', newline='\n', delete=False) as stream:
            stream.write(script)
            command_file = Path(stream.name)
        try:
            response = self.cm.access(dict(category=self.cmeta['uses_categories']['host'],
                command='run', arg1=worker, script=str(command_file), capture=True,
                timeout=50, quiet=True, con=False))
            if self.cm.catch_error(response):
                return response
            output = next(iter(response['outputs'].values()))
            if output['returncode']:
                return self.cm.error('Worker request failed: '+output.get('stderr', '')[-2000:])
            return {'return': 0, 'result': json.loads(output['stdout'])}
        finally:
            command_file.unlink(missing_ok=True)
