"""
Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.

Run every command of the converted CK programs (cBench, PolyBench/C) on one target and record what
each run did: its exit status, its time, the kernel time measured by xOpenME and the SHA-256 of
each output file. Then compare the records of several targets, compilers or hosts: a program and
command should produce the same outputs everywhere.

  cx task run test-ck-programs --compute=cpu --out=windows-msvc.json
  cx task run test-ck-programs --compute=android-cpu --out=android.json
  cx task run test-ck-programs --compare=windows-msvc.json,android.json

Each run is "cx program run <program> --compute=<compute> [--cmd=<command>] -q" in a process of its
own (a time limit per run, standard input closed), its output in <out>-logs/.
"""

import datetime
import fnmatch
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import time

from task_c36be4b9314a45e0.api.ctask import InitCTask

# How C libraries print a NaN: -nan(ind) (Windows), -nan / nan (glibc, macOS, bionic); its sign is
# not defined by IEEE 754 operations and differs between compilers
NAN_WORDS = re.compile(rb'[-+]?nan(\([a-z0-9_]*\))?', re.IGNORECASE)


class CTask(InitCTask):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, module_file_path = __file__, **kwargs)

    ############################################################
    def run(self,
            ctx: dict,
            programs: str = None,       # program aliases, comma-separated patterns (default: cbench-*,polybench-cpu-*)
            exclude: str = None,        # aliases or patterns to leave out
            repo: str = None,           # the repository of the programs (default: cmeta-ck-legacy)
            compute: str = 'cpu',       # the target of every run (cpu, android-cpu, ios-cpu ...)
            extra: str = None,          # more flags for every run ("--use.compiler-c.name=clang")
            out: str = None,            # the record of the runs (JSON); default ck-programs-<compute>.json
            timeout: int = 900,         # seconds per run
            compare: str = None,        # records to compare (comma-separated), instead of running
            fail: bool = False,         # return an error when a run fails or the outputs differ
            compile_only: bool = False, # only build each program (cx program compile): a target without a device
            all_datasets: bool = False, # each command on every dataset with its tags (CK's MiDataSets runs), not
                                        # only the default one
            datasets: str = None,       # with --all_datasets: only the datasets whose alias matches (patterns)
    ):
        """
        Run the commands of the programs and record them, or compare records (--compare).
        """

        con = ctx['control'].get('con', False)
        desc = self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {}

        if compare:
            return self._compare(con, [x.strip() for x in compare.split(',') if x.strip()],
                                 desc.get('not_compared') or [], fail, desc.get('host_dependent') or {})

        cx = shutil.which('cx') or shutil.which('cmeta')
        if not cx:
            return self.cm.error('cx is not on the PATH')

        r = self._programs(programs or desc.get('default_programs'), exclude, repo or desc.get('default_repo'))
        if r['return'] > 0: return r
        todo = r['programs']
        if not todo:
            return self.cm.error('no program matches')

        out = os.path.abspath(out or f'ck-programs-{compute.replace(",", "-")}.json')
        logs = os.path.splitext(out)[0] + '-logs'
        os.makedirs(logs, exist_ok = True)
        extra_args = shlex.split(extra) if extra else []
        # The checks of the outputs (checks of _desc.yaml), but for builds without the CPU reference
        checks = {} if any(a.lower() in ('--compile.check=no', '--compile.check=false') for a in extra_args) \
                 else (desc.get('checks') or {})
        # A build folder per target (the plain one holds the host's build): tmp-android-cpu, tmp-cuda ...
        if compute.strip().lower() != 'cpu' and not any(a.startswith('--target_tmp') for a in extra_args):
            extra_args.append('--target_tmp=tmp-' + '-'.join(c.strip().lower() for c in compute.split(',') if c.strip()))

        runs = []
        dataset_patterns = [p.strip() for p in (datasets or '').split(',') if p.strip()]
        for name, path, cmds, data in todo:
            for c in ([None] if compile_only else cmds):
                if all_datasets and not compile_only:
                    tags = self._dataset_tags(data, c)
                    if tags:
                        r = self._datasets(tags, dataset_patterns)
                        if r['return'] > 0: return r
                        runs += [(name, path, c, a) for a in r['aliases']]
                        continue
                runs.append((name, path, c, None))
        record = {'host': platform.node(), 'os': f'{platform.system()} {platform.release()}',
                  'machine': platform.machine(), 'compute': compute, 'extra': extra or '',
                  'mode': 'compile' if compile_only else ('all datasets' if all_datasets else 'run'),
                  'started': datetime.datetime.now().astimezone().isoformat(timespec = 'seconds'),
                  'runs': []}

        for n, (name, path, c, dataset) in enumerate(runs, 1):
            label = name + ('' if c is None else f' --cmd={c}') + ('' if dataset is None else f' --dataset={dataset}')
            log = os.path.join(logs, name + ('' if c is None else '--' + c) + ('' if dataset is None else '--' + dataset) + '.log')
            json_file = os.path.splitext(log)[0] + '.json'
            for f in (json_file,):
                if os.path.isfile(f):
                    os.remove(f)

            cmd = [cx, 'program', 'compile' if compile_only else 'run', name, f'--compute={compute}', '-q',
                   f'--json_file={json_file}']
            if c is not None:
                cmd.append(f'--cmd={c}')
            if dataset is not None:
                cmd.append(f'--dataset={dataset}')
            cmd += extra_args

            if con:
                print (f'[{n}/{len(runs)}] {label} ...', end = '', flush = True)

            started = time.monotonic()
            status = 'ok'
            with open(log, 'w', encoding = 'utf-8', errors = 'replace') as f:
                f.write(' '.join(shlex.quote(x) for x in cmd) + '\n\n')
                f.flush()
                try:
                    p = subprocess.run(cmd, stdin = subprocess.DEVNULL, stdout = f, stderr = subprocess.STDOUT,
                                       timeout = timeout)
                    rc = p.returncode
                except subprocess.TimeoutExpired:
                    rc, status = None, 'timeout'
            seconds = round(time.monotonic() - started, 3)

            result = {}
            if os.path.isfile(json_file):
                try:
                    with open(json_file, encoding = 'utf-8') as f:
                        result = json.load(f)
                except (OSError, ValueError):
                    result = {}
            if status == 'ok' and (rc != 0 or result.get('return', 1) != 0):
                status = 'failed'

            entry = {'program': name, 'cmd': c or 'default', 'status': status, 'rc': rc, 'seconds': seconds,
                     'log': os.path.relpath(log, os.path.dirname(out))}
            if dataset is not None:
                entry['dataset'] = dataset
            stats = result.get('stats-xopenme') or {}
            if 'execution_time_kernel_0' in stats:
                entry['kernel_seconds'] = stats['execution_time_kernel_0']

            build = os.path.dirname(((result.get('provenance') or {}).get('path')) or '')
            if build and os.path.isdir(build):
                entry['build'] = build
                if not compile_only:
                    entry['outputs'] = self._outputs(build)
                    if status == 'ok':
                        check = self._check(name, build, checks)
                        if check:
                            entry['check'] = check
                            if not check['ok']:
                                status = entry['status'] = 'check failed'
            if status != 'ok':
                entry['error'] = (entry['check']['note'] if status == 'check failed' else self._tail(log))

            record['runs'].append(entry)

            if con:
                x = f' {status} {seconds:.1f} s'
                if 'kernel_seconds' in entry:
                    x += f' (kernel {entry["kernel_seconds"]} s)'
                if entry.get('outputs'):
                    x += f', {len(entry["outputs"])} outputs'
                if entry.get('check', {}).get('ok'):
                    x += ', check ok'
                print (x, flush = True)

            with open(out, 'w', encoding = 'utf-8', newline = '\n') as f:
                json.dump(record, f, indent = 1)

        record['finished'] = datetime.datetime.now().astimezone().isoformat(timespec = 'seconds')
        with open(out, 'w', encoding = 'utf-8', newline = '\n') as f:
            json.dump(record, f, indent = 1)

        bad = [e for e in record['runs'] if e['status'] != 'ok']
        checked = [e for e in record['runs'] if e.get('check', {}).get('ok')]
        if con:
            print ('')
            for e in bad:
                x = f' --dataset={e["dataset"]}' if e.get('dataset') else ''
                print (f'{e["status"].upper():8} {e["program"]} --cmd={e["cmd"]}{x}: {e.get("error", "")[-300:]}')
            print (f'cMeta info: {len(record["runs"]) - len(bad)} of {len(record["runs"])} runs ok on {compute} '
                   f'({record["host"]})' + (f', {len(checked)} checked' if checks else '') + f'; the record: {out}')

        if fail and bad:
            return self.cm.error(f'{len(bad)} of {len(record["runs"])} runs failed (see {out})')
        return {'return': 0, 'out': out, 'ok': len(record['runs']) - len(bad), 'failed': len(bad)}

    ############################################################
    def _programs(self, patterns, exclude, repo):
        """(alias, path, [commands or None], _desc.yaml) of the programs of the repository that match."""
        wanted = [p.strip() for p in (patterns or '*').split(',') if p.strip()]
        skip = [p.strip() for p in (exclude or '').split(',') if p.strip()]

        r = self.cm.access({'category': self.cmeta['uses_categories']['program'], 'command': 'find',
                            'arg1': f'{repo}:*' if repo else '*', 'con': False})
        if r['return'] > 0: return r

        out = []
        for a in r.get('artifacts', []):
            path = a['path']
            name = os.path.basename(path)
            if not any(fnmatch.fnmatch(name, p) for p in wanted) or any(fnmatch.fnmatch(name, s) for s in skip):
                continue
            commands = [None]
            data = {}
            fp = os.path.join(path, '_desc.yaml')
            if os.path.isfile(fp):
                rr = self.cm.utils.files.read_file(fp)
                data = (rr.get('data') or {}) if rr['return'] == 0 else {}
                if isinstance(data.get('updates_cmd'), dict):
                    commands = sorted(data['updates_cmd'])
            out.append((name, path, commands, data))
        return {'return': 0, 'programs': sorted(out, key = lambda x: x[0])}

    def _dataset_tags(self, data, cmd):
        """The dataset tags of a command: its updates_cmd entry first, then the program's updates."""
        def find(x):
            if isinstance(x, dict):
                if str(x.get('task', '')).startswith('dataset,') and x.get('dataset_tags'):
                    return x['dataset_tags']
                if str((x.get('match') or {}).get('task', '')).startswith('dataset,') and (x.get('update') or {}).get('dataset_tags'):
                    return x['update']['dataset_tags']
                for v in x.values():
                    t = find(v)
                    if t:
                        return t
            elif isinstance(x, list):
                for v in x:
                    t = find(v)
                    if t:
                        return t
            return None
        tags = find(((data.get('updates_cmd') or {}).get(cmd) or {})) if cmd else None
        return tags or find(data.get('updates') or {})

    def _datasets(self, tags, patterns):
        """The aliases of the datasets with these tags (sorted), those that match the patterns when there are some."""
        r = self.cm.access({'category': 'dataset', 'command': 'find', 'tags': tags, 'con': False})
        if r['return'] > 0: return r
        aliases = sorted({os.path.basename(a['path']) for a in r.get('artifacts', [])})
        if patterns:
            aliases = [a for a in aliases if any(fnmatch.fnmatch(a, p) for p in patterns)]
        return {'return': 0, 'aliases': aliases}

    def _check(self, name, build, checks):
        """
        The check of a run's output (checks of _desc.yaml, by program pattern): {ok, values, note}, or None when
        the program has none. Every match of the regular expression in the file must give expect.
        """
        spec = next((v for p, v in checks.items() if fnmatch.fnmatch(name, p)), None)
        if not spec:
            return None
        try:
            with open(os.path.join(build, spec['file']), encoding = 'utf-8', errors = 'replace') as f:
                values = re.findall(spec['regex'], f.read())
        except OSError:
            return {'ok': False, 'values': [], 'note': f'no {spec["file"]} to check'}
        if not values:
            return {'ok': False, 'values': [], 'note': f'no line of the check in {spec["file"]} ({spec["regex"]})'}
        ok = all(str(v) == str(spec['expect']) for v in values)
        note = '' if ok else f'{spec.get("what") or "check"}: {", ".join(values)} (expected {spec["expect"]})'
        return {'ok': ok, 'values': values, 'note': note}

    ############################################################
    def _outputs(self, build):
        """{file: {size, sha256}} of the output files the run listed (its _repro_ctx_run.json)."""
        names = []
        fp = os.path.join(build, '_repro_ctx_run.json')
        if os.path.isfile(fp):
            try:
                with open(fp, encoding = 'utf-8') as f:
                    names = ((json.load(f).get('ctx') or {}).get('tasks') or {}).get('local', {}).get('output_files') or []
            except (OSError, ValueError):
                names = []
        out = {}
        for name in names:
            p = os.path.join(build, name)
            if os.path.isfile(p):
                with open(p, 'rb') as f:
                    data = f.read()
                # sha256_lf: the digest with Windows' line ends (\r\n) read as \n - a text file written in
                # text mode on Windows equals the one of Linux then; sha256_nan: also every NaN spelled "nan"
                # (a text file only: no byte 0)
                lf = data.replace(b'\r\n', b'\n')
                out[name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                             'sha256_lf': hashlib.sha256(lf).hexdigest()}
                if b'\0' not in data:
                    out[name]['sha256_nan'] = hashlib.sha256(NAN_WORDS.sub(b'nan', lf)).hexdigest()
            else:
                out[name] = None
        return out

    def _tail(self, log, lines = 12):
        try:
            with open(log, encoding = 'utf-8', errors = 'replace') as f:
                text = [l.rstrip() for l in f.readlines() if l.strip()]
        except OSError:
            return ''
        return ' | '.join(text[-lines:])

    ############################################################
    def _compare(self, con, files, not_compared, fail, host_dependent = None):
        """
        Compare the records: per program and command, the status everywhere and whether the outputs agree.
        host_dependent: {"<program>[ <command>]": {file: why}} - outputs that hold a path or a time of the
        host (named, not compared).
        """
        host_dependent = host_dependent or {}
        records = []
        for f in files:
            if not os.path.isfile(f):
                return self.cm.error(f'no record "{f}"')
            with open(f, encoding = 'utf-8') as x:
                records.append(json.load(x))

        names = [f'{os.path.splitext(os.path.basename(f))[0]}' for f in files]
        keys = []
        for rec in records:
            for e in rec['runs']:
                k = (e['program'], e['cmd'], e.get('dataset') or '')
                if k not in keys:
                    keys.append(k)

        rows = []
        differ = 0
        for k in sorted(keys):
            entries = [next((e for e in rec['runs'] if (e['program'], e['cmd'], e.get('dataset') or '') == k), None)
                       for rec in records]
            statuses = [e['status'] if e else '-' for e in entries]
            ok = [e for e in entries if e and e['status'] == 'ok']

            verdict = ''
            groups = {}
            if len(ok) >= 2:
                ok_names = [n for n, e in zip(names, entries) if e and e['status'] == 'ok']
                files_all = sorted({n for e in ok for n in (e.get('outputs') or {}) if n not in not_compared})
                host = (host_dependent.get(f'{k[0]} {k[1]}') or host_dependent.get(k[0]) or
                        next((v for p_, v in host_dependent.items() if fnmatch.fnmatch(k[0], p_)), {}))
                diff, line_ends, nans, by_host = [], [], [], []
                for n in files_all:
                    if n in host:
                        by_host.append(n)
                        continue
                    outs = [((e.get('outputs') or {}).get(n) or {}) for e in ok]
                    if len({o.get('sha256') for o in outs}) == 1:
                        continue
                    lf = [o.get('sha256_lf') or o.get('sha256') for o in outs]
                    if len(set(lf)) == 1:
                        line_ends.append(n)
                        continue
                    if all(o.get('sha256_nan') for o in outs) and len({o['sha256_nan'] for o in outs}) == 1:
                        nans.append(n)
                        continue
                    diff.append(n)
                    # which records agree with which (A = the first one's output, B the next one ...)
                    labels = {}
                    groups[n] = ' '.join(f'{rn}={labels.setdefault(d, "ABCDEFGH"[len(labels)])}' for rn, d in zip(ok_names, lf))
                notes = []
                if line_ends:
                    notes.append('line ends: ' + ', '.join(line_ends))
                if nans:
                    notes.append('NaN printed otherwise: ' + ', '.join(nans))
                if by_host:
                    notes.append('not compared: ' + '; '.join(f'{n} - {host[n]}' for n in by_host))
                if diff:
                    verdict = 'DIFFER: ' + ', '.join(diff)
                    differ += 1
                else:
                    verdict = 'same'
                if notes:
                    verdict += ' (' + '; '.join(notes) + ')'
            rows.append({'program': k[0], 'cmd': k[1] + (f' {k[2]}' if k[2] else ''), 'status': dict(zip(names, statuses)),
                         'outputs': verdict,
                         'groups': groups})

        if con:
            w = max(len(f'{r["program"]} {r["cmd"]}') for r in rows)
            print (f'{"program command":{w}}  ' + '  '.join(f'{n:>12}' for n in names) + '  outputs')
            for r in rows:
                print (f'{r["program"] + " " + r["cmd"]:{w}}  ' + '  '.join(f'{r["status"][n]:>12}' for n in names)
                       + '  ' + r['outputs'])
                for f, g in r['groups'].items():
                    print (f'{"":{w}}    {f}: {g}')
            print ('')
            print (f'cMeta info: {len(rows)} program commands, {differ} with outputs that differ; '
                   + ', '.join(f'{n}: {sum(1 for r in rows if r["status"][n] == "ok")} ok' for n in names))

        if fail and (differ or any(s not in ('ok', '-') for r in rows for s in r['status'].values())):
            return self.cm.error('runs failed or outputs differ')
        return {'return': 0, 'rows': rows, 'differ': differ}
