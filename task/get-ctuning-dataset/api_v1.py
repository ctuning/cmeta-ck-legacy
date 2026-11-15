"""
Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.

The full cBench inputs (cTuning MiDataSets) on demand. They are in capsules, one per kind of input
(20261115.ctuning-midatasets.image-ppm.tar.gz holds the 20 PPM images ...). run() puts one capsule into
the cache entry of this task (one entry per capsule: cache_params): copied from a folder or downloaded,
its SHA-256 compared with the index, unpacked, every file checked. finish_dynamic_result() then gives
the files of the entry asked for, also when the capsule comes from the cache:

  path        the entry's first file (CK's order: the file a program takes by default)
  path_entry  the entry's folder
  files       the entry's files in CK's order (a program that takes several reads them from here)

A dataset artifact asks for it in its _desc.yaml (uses + result_from_ctx):

  uses:
    - task: get-ctuning-dataset,e4bfa3539ac64d5f
      capsule: image-ppm
      entry: image-ppm-0007
  result_from_ctx: '{{global.get-ctuning-dataset}}'

  cx task run get-ctuning-dataset image-ppm image-ppm-0007 --capsules=<folder or URL with {name}>
"""

import hashlib
import json
import os
import shutil
import tarfile

from task_c36be4b9314a45e0.api.ctask import InitCTask

CONFIG = 'task-get-ctuning-dataset'


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class CTask(InitCTask):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, module_file_path = __file__, **kwargs)

    ############################################################
    def run(self,
            ctx: dict,
            capsule: str = None,        # the kind of input: image-ppm, audio-wav, txt, number ...
            entry: str = None,          # the entry of the capsule (image-ppm-0007); its files come with the result
            capsules: str = None,       # where the capsules are: a folder, or a URL with {name}
            check: bool = True,         # compare every unpacked file with the SHA-256 of the index
    ):
        """
        Put a capsule of the cTuning MiDataSets into this cache entry (the working folder) and unpack it.
        """

        con = ctx['control'].get('con', False)

        r = self._capsule_record(capsule, entry)
        if r['return'] > 0: return r
        rec = r['record']

        # The places to try, in order: those given (--capsules, else this machine's setting - several
        # separated by ";"), then the place where the capsule's set is published
        given = capsules or self._configured()
        places = [x.strip() for x in str(given or '').split(';') if x.strip()]
        for x in (r.get('url'), self._desc().get('capsules')):
            if x and x not in places:
                places.append(x)
        if not places:
            return self.cm.error(f'no place for the capsule "{capsule}" yet: give --capsules=<folder, or a URL '
                                 f'with {{name}}> or set it for this machine (cx config set {CONFIG} --meta.capsules=...)')

        work = os.getcwd()
        name = rec['capsule']
        target = os.path.join(work, name)

        errors = []
        for source in places:
            if source.startswith(('http://', 'https://')):
                url = source.replace('{name}', name) if '{name}' in source else source.rstrip('/') + '/' + name
                if con:
                    print (f'cMeta info: downloading {name} ({rec["size"] / 1e6:.1f} MB) from {url}')
                rr = self.cm.utils.net.download(url, filename = name + '.download', path = work, show_progress = con)
                if rr['return'] > 0:
                    errors.append(f'{url}: {rr.get("error")}')
                    continue
                os.replace(os.path.join(work, name + '.download'), target)
                break
            src = os.path.join(os.path.expanduser(source), name)
            if not os.path.isfile(src):
                errors.append(f'not in "{source}"')
                continue
            if con:
                print (f'cMeta info: copying {name} ({rec["size"] / 1e6:.1f} MB) from {source}')
            shutil.copyfile(src, target)
            break
        else:
            return self.cm.error(f'capsule "{name}" not found: ' + '; '.join(errors))

        digest = sha256_of(target)
        if digest != rec['sha256']:
            os.remove(target)
            return self.cm.error(f'capsule "{name}" has the SHA-256 {digest}, not {rec["sha256"]} of the index')

        r = self._unpack(target, work)
        if r['return'] > 0: return r
        os.remove(target)

        if check:
            bad = []
            for e, x in rec['entries'].items():
                for f in x['files']:
                    p = os.path.join(work, e, f['name'])
                    if not os.path.isfile(p) or sha256_of(p) != f['sha256']:
                        bad.append(f'{e}/{f["name"]}')
            if bad:
                return self.cm.error(f'capsule "{name}": {len(bad)} files differ from the index: {", ".join(bad[:5])}')

        if con:
            print (f'cMeta info: {len(rec["entries"])} entries of "{capsule}" in {work}')

        return {'return': 0, 'path_root': work, 'capsule': capsule, 'capsule_file': name, 'capsule_sha256': digest,
                'entries': sorted(rec['entries'])}

    ############################################################
    def finish_dynamic_result(self,
                              ctx: dict,
                              result: dict = {},
                              params: dict = {},
    ):
        """The files of the entry asked for (params.entry), from the capsule's folder (also from the cache)."""

        entry = params.get('entry')
        root = result.get('path_root')
        if not entry or not root:
            return {'return': 0}

        r = self._capsule_record(params.get('capsule'), entry)
        if r['return'] > 0: return r
        x = r['record']['entries'][entry]

        folder = os.path.join(root, entry)
        files = list(x.get('order') or [f['name'] for f in x['files']])
        path = os.path.join(folder, files[0]) if files else folder

        result = dict(result)
        result.update({'entry': entry, 'path_entry': folder, 'files': files, 'path': path,
                       'qpath': self.cm.q(path), 'tags': x.get('tags') or []})
        if x.get('number') is not None:
            result['number'] = str(x['number'])

        return {'return': 0, 'result': result}

    ############################################################
    def _desc(self):
        return self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {}

    def _indexes(self):
        """[(index, url of its set)] of the sets of capsules ("indexes" of _desc.yaml)."""
        out = []
        for x in self._desc().get('indexes') or []:
            path = os.path.join(self.artifact_path, x.get('index') or '')
            try:
                with open(path, encoding = 'utf-8') as f:
                    out.append((json.load(f), str(x.get('url') or '').strip()))
            except (OSError, ValueError) as e:
                return self.cm.error(f'the index of the capsules "{path}" cannot be read: {e}')
        return {'return': 0, 'indexes': out}

    def _capsule_record(self, capsule, entry):
        """The record of a capsule in the indexes, the place of its set (and a check that the entry is one of its)."""
        r = self._indexes()
        if r['return'] > 0: return r
        names = sorted(c for index, _ in r['indexes'] for c in index['capsules'])
        if not capsule:
            return self.cm.error('--capsule=<kind> is needed: ' + ', '.join(names))
        for index, url in r['indexes']:
            rec = index['capsules'].get(capsule)
            if rec is None:
                continue
            if entry and entry not in rec['entries']:
                return self.cm.error(f'no entry "{entry}" in the capsule "{capsule}"; there are: ' + ', '.join(sorted(rec['entries'])))
            return {'return': 0, 'record': rec, 'url': url, 'tags': index.get('tags') or []}
        return self.cm.error(f'no capsule "{capsule}"; there are: ' + ', '.join(names))

    def _configured(self):
        """This machine's place of the capsules (config task-get-ctuning-dataset, key capsules)."""
        r = self.cm.access({'category': 'config', 'command': 'read', 'arg1': CONFIG, 'con': False})
        if r.get('return', 1) > 0:
            return ''
        return str((r.get('config_cmeta') or {}).get('capsules') or '').strip()

    def _unpack(self, archive, dest):
        """Unpack a capsule: regular files and folders only, every name inside dest."""
        root = os.path.realpath(dest)
        with tarfile.open(archive, 'r:gz') as tar:
            for m in tar.getmembers():
                p = os.path.realpath(os.path.join(root, m.name))
                if not (p == root or p.startswith(root + os.sep)) or not (m.isfile() or m.isdir()):
                    return self.cm.error(f'capsule "{os.path.basename(archive)}": member "{m.name}" refused')
                if m.isdir():
                    os.makedirs(p, exist_ok = True)
                    continue
                os.makedirs(os.path.dirname(p), exist_ok = True)
                with tar.extractfile(m) as src, open(p, 'wb') as out:
                    shutil.copyfileobj(src, out)
        return {'return': 0}
