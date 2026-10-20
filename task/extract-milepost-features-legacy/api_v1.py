"""Extract historical MILEPOST features through a private cMeta worker.

Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from task_c36be4b9314a45e0.api.ctask import InitCTask


class CTask(InitCTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module_file_path=__file__, **kwargs)

    def run(self, ctx, source_file: str='', output_file: str='', worker: str='',
            runtime_root: str='', endpoint: str=''):
        """Extract 55 static features from C89 source; runtime-root selects native Linux execution."""
        try:
            runtime_root = runtime_root or os.environ.get('CMETA_MILEPOST_ROOT', '')
            if not (runtime_root or worker or endpoint):
                return self.cm.error('Provide --runtime-root=<prepared legacy runtime> for direct Linux/container execution; no website endpoint is selected automatically')
            source = Path(source_file).read_text(encoding='utf-8')
            if not source.strip() or len(source.encode())>65536:
                return self.cm.error('Provide nonempty C source of at most 64 KiB')
            request = json.dumps({'source': source})
            if endpoint:
                try:
                    response=urllib.request.urlopen(urllib.request.Request(endpoint,data=request.encode(),
                        headers={'Content-Type':'application/json'}),timeout=40)
                except urllib.error.HTTPError as error:
                    response=error
                with response:
                    result=json.load(response)
            elif runtime_root:
                if sys.platform!='linux':
                    return self.cm.error('Direct extraction requires Linux amd64; run cMeta inside a compatible Linux container or VM')
                process = subprocess.run([sys.executable, str(Path(__file__).parent/'src/milepost.py'),
                                          'extract', '--root', runtime_root], input=request,
                                         text=True, capture_output=True, timeout=45)
                if process.returncode:
                    return self.cm.error('Native extraction failed: '+process.stderr[-2000:])
                result = json.loads(process.stdout)
            else:
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
                    result = json.loads(output['stdout'])
                finally:
                    command_file.unlink(missing_ok=True)
            if output_file:
                written = self.cm.utils.files.safe_write_file(output_file, result, atomic=True)
                if self.cm.catch_error(written):
                    return written
            if not result.get('ok'):
                return {'return': 1, 'error': result.get('error', 'Feature extraction failed'), 'extraction': result}
            print(result['features'])
            return {'return': 0, 'extraction': result}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            return self.cm.error(str(error))
