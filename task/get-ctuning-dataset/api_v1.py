"""
Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.

The full cBench inputs (cTuning MiDataSets) and the office snapshots of the CK paper on demand. A set of inputs is
either a capsule - one archive per kind of input (20261115.ctuning-midatasets.image-ppm.tar.gz holds the 20 PPM
images) - or files published one by one (the office snapshots: dataset.ctuning-image-jpg-fgg-office.day.data_orig.jpg
...); an index (indexes of _desc.yaml) lists the sets, their inputs and the SHA-256 of everything. run() puts one set
into the cache entry of this task (one entry per set: cache_params): copied from a folder or downloaded, checked, a
capsule unpacked - a folder per input, <input>/<files>, the layout of a dataset's files/ with sub-datasets.

A dataset artifact asks for it in its _desc.yaml (uses + result_from_ctx) and takes its sub-datasets from path_root
of the result:

  sub_datasets:
    image-ppm-0001: {files: [data.ppm]}
    ...
  uses:
    - task: get-ctuning-dataset,e4bfa3539ac64d5f
      capsule: image-ppm
  result_from_ctx: '{{global.get-ctuning-dataset}}'

  cx task run get-ctuning-dataset image-ppm --capsules=<folder, or URL with {name}>
  cx task run get-ctuning-dataset image-ppm image-ppm-0007     # one input: its files in the result (path, files ...)

finish_dynamic_result() gives the files of the input asked for (also when the set comes from the cache):

  path        the input's first file (CK's order: the file a program takes by default)
  path_entry  the input's folder
  files       the input's files in CK's order (a program that takes several reads them from here)
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
            capsule: str = None,        # the set of inputs: a kind of cBench input (image-ppm, audio-wav, txt, number ...),
                                        # a set of the office snapshots (image-jpg-fgg-office)
            entry: str = None,          # one input of the set (image-ppm-0007): its files come with the result
            capsules: str = None,       # where the capsules or files are: a folder, or a URL with {name}
            check: bool = True,         # compare every file with the SHA-256 of the index
    ):
        """
        Put a set of inputs into this cache entry (the working folder): a capsule unpacked, or its files one by one.
        """

        con = ctx['control'].get('con', False)

        r = self._capsule_record(capsule, entry)
        if r['return'] > 0: return r
        rec = r['record']

        # The places to try, in order: those given (--capsules, else this machine's setting - several
        # separated by ";"), then the place where the set is published
        given = capsules or self._configured()
        places = [x.strip() for x in str(given or '').split(';') if x.strip()]
        for x in (r.get('url'), self._desc().get('capsules')):
            if x and x not in places:
                places.append(x)
        if not places:
            return self.cm.error(f'no place for the set "{capsule}" yet: give --capsules=<folder, or a URL '
                                 f'with {{name}}> or set it for this machine (cx config set {CONFIG} --meta.capsules=...)')

        work = os.getcwd()
        result = {'return': 0, 'path_root': work, 'capsule': capsule, 'entries': sorted(rec['entries'])}

        if rec.get('capsule'):
            # A capsule: the archive, checked and unpacked
            name = rec['capsule']
            target = os.path.join(work, name)
            r = self._fetch(places, name, target, rec.get('size'), con)
            if r['return'] > 0: return r

            digest = sha256_of(target)
            if digest != rec['sha256']:
                os.remove(target)
                return self.cm.error(f'capsule "{name}" has the SHA-256 {digest}, not {rec["sha256"]} of the index')

            r = self._unpack(target, work)
            if r['return'] > 0: return r
            os.remove(target)
            result.update({'capsule_file': name, 'capsule_sha256': digest})

        else:
            # Files published one by one ("file" of each file of the index: its published name): every input of
            # the set, into <input>/<name>
            for e, x in sorted(rec['entries'].items()):
                os.makedirs(os.path.join(work, e), exist_ok = True)
                for f in x['files']:
                    r = self._fetch(places, f.get('file') or f['name'], os.path.join(work, e, f['name']), f.get('size'), con)
                    if r['return'] > 0: return r
            result['capsule_file'] = ''

        if check:
            bad = []
            for e, x in rec['entries'].items():
                for f in x['files']:
                    p = os.path.join(work, e, f['name'])
                    if not os.path.isfile(p) or sha256_of(p) != f['sha256']:
                        bad.append(f'{e}/{f["name"]}')
            if bad:
                return self.cm.error(f'set "{capsule}": {len(bad)} files differ from the index: {", ".join(bad[:5])}')

        if con:
            print (f'cMeta info: {len(rec["entries"])} inputs of "{capsule}" in {work}')

        return result

    ############################################################
    def finish_dynamic_result(self,
                              ctx: dict,
                              result: dict = {},
                              params: dict = {},
    ):
        """The files of the input asked for (params.entry), from the set's folder (also from the cache)."""

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
    def _fetch(self, places, name, target, size, con):
        """A published file (name) into target, from the first place that has it: a URL downloaded, a folder copied."""

        mb = f' ({size / 1e6:.1f} MB)' if isinstance(size, (int, float)) else ''
        work = os.path.dirname(target)
        errors = []
        for source in places:
            if source.startswith(('http://', 'https://')):
                url = source.replace('{name}', name) if '{name}' in source else source.rstrip('/') + '/' + name
                if con:
                    print (f'cMeta info: downloading {name}{mb} from {url}')
                rr = self.cm.utils.net.download(url, filename = os.path.basename(target) + '.download', path = work, show_progress = con)
                if rr['return'] > 0:
                    errors.append(f'{url}: {rr.get("error")}')
                    continue
                os.replace(target + '.download', target)
                return {'return': 0}
            src = os.path.join(os.path.expanduser(source), name)
            if not os.path.isfile(src):
                errors.append(f'not in "{source}"')
                continue
            if con:
                print (f'cMeta info: copying {name}{mb} from {source}')
            shutil.copyfile(src, target)
            return {'return': 0}
        return self.cm.error(f'"{name}" not found: ' + '; '.join(errors))

    ############################################################
    def _desc(self):
        return self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {}

    def _indexes(self):
        """[(index, url of its set)] of the sets of inputs ("indexes" of _desc.yaml)."""
        out = []
        for x in self._desc().get('indexes') or []:
            path = os.path.join(self.artifact_path, x.get('index') or '')
            try:
                with open(path, encoding = 'utf-8') as f:
                    out.append((json.load(f), str(x.get('url') or '').strip()))
            except (OSError, ValueError) as e:
                return self.cm.error(f'the index "{path}" cannot be read: {e}')
        return {'return': 0, 'indexes': out}

    def _capsule_record(self, capsule, entry):
        """The record of a set in the indexes, the place where it is published (and a check that the entry is one of its)."""
        r = self._indexes()
        if r['return'] > 0: return r
        names = sorted(c for index, _ in r['indexes'] for c in index['capsules'])
        if not capsule:
            return self.cm.error('--capsule=<set> is needed: ' + ', '.join(names))
        for index, url in r['indexes']:
            rec = index['capsules'].get(capsule)
            if rec is None:
                continue
            if entry and entry not in rec['entries']:
                return self.cm.error(f'no input "{entry}" in the set "{capsule}"; there are: ' + ', '.join(sorted(rec['entries'])))
            return {'return': 0, 'record': rec, 'url': url, 'tags': index.get('tags') or []}
        return self.cm.error(f'no set "{capsule}"; there are: ' + ', '.join(names))

    def _configured(self):
        """This machine's place of the capsules and files (config task-get-ctuning-dataset, key capsules)."""
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
