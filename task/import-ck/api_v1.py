"""
Licensed under the Apache License, Version 2.0.
See the LICENSE file in the project root for details.

Convert programs and datasets of the Collective Knowledge (CK) format into cMeta artifacts:
a CK program (.cm/meta.json: source_files, compile_deps, build_compiler_vars, run_cmds with
dataset_tags) becomes a program that inherits template-c-cpu, and a CK dataset (.cm/meta.json:
tags, dataset_files) becomes a dataset with its files in files/.

The sources are CK's, changed only where they would not build or run on every target:
- PolyBench (every kernel): the printf format of DATA_TYPE chosen by token pasting (MSVC refuses
  "#if DATA_TYPE == double"), and the arrays dumped into tmp-ck-output-dump.txt instead of the
  standard streams (an iOS app has no redirection);
- files/patches/<CK program>.patch: a unified diff of one program's sources, applied as it is
  (the lines starting with "# " before the first file say what it changes and why).
"""

import datetime
import fnmatch
import json
import os
import re
import shutil

from task_c36be4b9314a45e0.api.ctask import InitCTask

TEMPLATE = 'template-c-cpu,649899ef3f004e4a'
TEMPLATE_CK = 'template-ck-program,f7fab3bed78041d1'      # cmeta-aops: the hooks of every converted program
TASK_SETUP = 'setup,a2f9b61079ce4333'
TASK_DATASET = 'dataset,30e20c7489f14f84'
TASK_SETUP_RUN = 'setup-run,148f6c1fdb4247df'
LIB_XOPENME = 'lib-xopenme,c7b96678a7734510'
LIB_POLYBENCH = 'lib-polybench,70349e61a532455d'
LIB_SYSROOT_ANDROID = 'lib-sysroot-android,cdc22b7617f54f2c'
LIB_CUDA = 'lib-cuda,ac9daedec465409e'
LIB_OPENCL = 'lib-opencl,c209094321c94530'   # cmeta-aops: the OpenCL headers and the library to link

SUITES = {
    'cbench': 'cBench (MiBench-based, cTuning)',
    'polybench': 'PolyBench/C 3.2 (Ohio State University), CK version',
    'polybench-cuda': 'PolyBench/GPU 1.0 CUDA (Ohio State University, University of Delaware), CK version',
    'polybench-opencl': 'PolyBench/GPU 1.0 OpenCL (Ohio State University, University of Delaware), CK version',
    'ck-codelet': 'Codelets of the CK paper repository (reproduce-ck-paper): edge detection of an image',
}

DOC_FILES = ('readme', 'license', 'licence', 'copying', 'copyright')

# PolyBench: the compile variables that are not sizes, and the file the arrays are dumped into
POLYBENCH_NOT_SIZES = ('DATA_TYPE', 'POLYBENCH_DUMP_ARRAYS', 'POLYBENCH_PADDING_FACTOR', 'XOPENME')
POLYBENCH_DUMP_FILE = 'tmp-ck-output-dump.txt'

POLYBENCH_FORMAT_BLOCK = re.compile(r'^# if DATA_TYPE == double\n.*?^# endif\n', re.M | re.S)

POLYBENCH_FORMAT = '''\
/* The printf format of DATA_TYPE (cMeta, task::import-ck: MSVC refuses "#if DATA_TYPE == double").
 * Two levels of macros expand DATA_TYPE before ## pastes it into the name of its format:
 * -DDATA_TYPE=double -> DATA_TYPE_double_FMT -> "%0.2lf " (C89, MSVC, GCC, Clang). */
# define DATA_TYPE_double_FMT "%0.2lf "
# define DATA_TYPE_float_FMT  "%0.2f "
# define DATA_TYPE_long_FMT   "%ld "
# define DATA_TYPE_int_FMT    "%d "

# define DATA_PRINTF_MODIFIER_PASTE(t) DATA_TYPE_ ## t ## _FMT
# define DATA_PRINTF_MODIFIER_EXPAND(t) DATA_PRINTF_MODIFIER_PASTE(t)
# define DATA_PRINTF_MODIFIER DATA_PRINTF_MODIFIER_EXPAND(DATA_TYPE)
'''

POLYBENCH_DUMP_HELPERS = '''\
/* cMeta (task::import-ck): print_array writes the arrays into a file rather than the standard
   streams, so that the dump comes back from every target (an iOS app has no redirection) */
static FILE *ck_dump_open(void)
{
  FILE *f = fopen("''' + POLYBENCH_DUMP_FILE + '''", "w");
  return f != NULL ? f : stderr;
}

static void ck_dump_close(FILE *f)
{
  if (f != stderr)
    fclose(f);
}

'''


CUDA_COMPAT = '''\
/* cMeta (task::import-ck): CUDA 13 removed cudaThreadSynchronize() (deprecated since CUDA 4) and
   cudaDeviceProp::computeMode. From CUDA 13 on (CUDART_VERSION, set by the headers of the CUDA runtime
   that nvcc includes), the current calls do the same; an older CUDA keeps the original ones. */
#if defined(CUDART_VERSION) && CUDART_VERSION >= 13000
#define cudaThreadSynchronize cudaDeviceSynchronize
#endif

static int ck_compute_mode_prohibited(int device, const cudaDeviceProp *prop)
{
#if defined(CUDART_VERSION) && CUDART_VERSION >= 13000
  int mode = 0;
  (void) prop;
  cudaDeviceGetAttribute(&mode, cudaDevAttrComputeMode, device);
  return mode == cudaComputeModeProhibited;
#else
  (void) device;
  return prop->computeMode == cudaComputeModeProhibited;
#endif
}

'''


def q(s):
    """A single-quoted YAML scalar."""
    return "'" + str(s).replace("'", "''") + "'"


def read_text(path):
    """A source file as text with \\n line ends, its encoding and its own line end (kept on write)."""
    with open(path, 'rb') as f:
        data = f.read()
    try:
        text, encoding = data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        text, encoding = data.decode('latin-1'), 'latin-1'
    newline = '\r\n' if '\r\n' in text else '\n'
    return text.replace('\r\n', '\n'), encoding, newline


CPU_CHECK_BLOCK = re.compile(r'^[ \t]*/\*[ \t]*\n(.*?)^[ \t]*\*/[ \t]*$', re.M | re.S)

# The arrays of a PolyBench/GPU main(): (DATA_TYPE*)malloc(<n>*sizeof(DATA_TYPE))
MALLOC_DATA = re.compile(r'\(DATA_TYPE\s*\*\)\s*malloc\(\s*(.+?)\s*\*\s*sizeof\(DATA_TYPE\)\s*\)')
MALLOC_ANY = re.compile(r'\(DATA_TYPE\s*\*\)\s*malloc\(')


def zeroed_arrays(text):
    """
    The arrays of main() allocated zeroed (calloc instead of malloc): (text, number changed), or (text, -1) when
    an allocation of main() has another form.
    """
    main = text.find('int main(')
    if main < 0:
        return text, 0
    head, body = text[:main], text[main:]
    if len(MALLOC_ANY.findall(body)) != len(MALLOC_DATA.findall(body)):
        return text, -1
    body, n = MALLOC_DATA.subn(lambda m: f'(DATA_TYPE*)calloc({m.group(1)}, sizeof(DATA_TYPE))', body)
    return head + body, n


def cpu_check_block(text):
    """
    The commented CPU reference of a PolyBench/GPU main() (the comment block, on lines of its own, that holds
    xopenme_clock_start(1)) as an #ifdef CK_CPU_CHECK block: (text, number of blocks changed).
    """
    main = text.find('int main(')
    if main < 0:
        return text, 0
    found = [m for m in CPU_CHECK_BLOCK.finditer(text, main) if 'xopenme_clock_start(1)' in m.group(1)]
    if len(found) != 1:
        return text, len(found)
    m = found[0]
    block = ('#ifdef CK_CPU_CHECK   /* cMeta: the CPU reference, a comment in the CK version */\n' + m.group(1) +
             '#endif /* CK_CPU_CHECK */')
    return text[:m.start()] + block + text[m.end():], 1


def write_text(path, text, encoding, newline):
    with open(path, 'wb') as f:
        f.write(text.replace('\n', newline).encode(encoding))


def parse_patch(text):
    """
    A unified diff (diff -u, git diff): its description (the lines "# ..." before the first file)
    and its files, each with its hunks (old start, old lines, new lines).
    """
    lines = text.replace('\r\n', '\n').split('\n')
    description = []
    files = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('--- ') and i + 1 < len(lines) and lines[i + 1].startswith('+++ '):
            name = lines[i + 1][4:].split('\t')[0].strip()
            if name.startswith('b/'):
                name = name[2:]
            hunks = []
            i += 2
            while i < len(lines) and lines[i].startswith('@@'):
                m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', lines[i])
                if not m:
                    raise ValueError(f'bad hunk header "{lines[i]}"')
                old_left = int(m.group(2)) if m.group(2) is not None else 1
                new_left = int(m.group(4)) if m.group(4) is not None else 1
                old, new = [], []
                i += 1
                while old_left > 0 or new_left > 0:
                    if i >= len(lines):
                        raise ValueError(f'the patch of "{name}" ends inside a hunk')
                    x = lines[i]
                    if x.startswith('\\'):          # \ No newline at end of file
                        i += 1
                        continue
                    kind, body = (x[:1], x[1:]) if x else (' ', '')
                    if kind == ' ':
                        old.append(body); new.append(body); old_left -= 1; new_left -= 1
                    elif kind == '-':
                        old.append(body); old_left -= 1
                    elif kind == '+':
                        new.append(body); new_left -= 1
                    else:
                        raise ValueError(f'bad line in a hunk of "{name}": "{x}"')
                    i += 1
                hunks.append((int(m.group(1)), old, new))
            files.append((name, hunks))
            continue
        if not files and line.startswith('#   ') and description:
            description[-1] += ' ' + line[2:].strip()        # a continued line
        elif not files and line.startswith('# '):
            description.append(line[2:].strip())
        i += 1
    return description, files


def apply_hunks(lines, hunks):
    """The lines with the hunks applied; each hunk's old lines must be found exactly once (or at its place)."""
    delta = 0
    for start, old, new in hunks:
        at = start - 1 + delta if old else start + delta
        if old and lines[at:at + len(old)] != old:
            found = [k for k in range(len(lines) - len(old) + 1) if lines[k:k + len(old)] == old]
            if len(found) != 1:
                return None
            at = found[0]
        lines = lines[:at] + new + lines[at + len(old):]
        delta += len(new) - len(old)
    return lines


class CTask(InitCTask):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, module_file_path = __file__, **kwargs)

    ############################################################
    def run(self,
            ctx: dict,
            ck_path: str = None,        # a CK repository (its program/ and dataset/ folders)
            programs: str = None,       # CK program aliases, comma-separated patterns (cbench-*,polybench-cpu-*)
            datasets: str = None,       # CK dataset aliases, comma-separated patterns
            exclude: str = None,        # aliases or patterns to leave out ('skip' is a control word of tasks)
            to: str = 'cmeta-ck-legacy',  # the cMeta repository that receives the artifacts
            ck_repo: str = None,        # the name of the CK repository, recorded in each artifact (default: the folder's)
            force: bool = False,        # rewrite artifacts that exist in the receiving repository
            dry_run: bool = False,      # only say what would be made
            midatasets: str = None,     # entries of the cTuning MiDataSets capsules (patterns): a dataset each,
                                        # its files from task::get-ctuning-dataset on demand (no CK folder needed)
            licenses_md: bool = False,  # write LICENSES.md at the root of "to": the licence of every artifact
    ):
        """
        Convert CK programs and datasets into cMeta artifacts of the repository "to".
        """

        con = ctx['control'].get('con', False)
        desc = self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {}
        skip_patterns = [s.strip() for s in (exclude or '').split(',') if s.strip()]
        report = []

        if midatasets:
            r = self._import_midatasets(midatasets, skip_patterns, to, desc.get('datasets') or {}, force, dry_run)
            if r['return'] > 0: return r
            report += r['report']

        if not programs and not datasets:
            if not midatasets and not licenses_md:
                return self.cm.error('nothing to convert: give --programs=<patterns>, --datasets=<patterns>, '
                                     '--midatasets=<patterns> or --licenses_md')
        elif not ck_path or not os.path.isdir(ck_path):
            return self.cm.error(f'--ck_path=<a CK repository folder> is needed (got "{ck_path}")')
        else:
            ck_path = os.path.abspath(ck_path)
            ck_repo = ck_repo or self._ck_repo_name(ck_path)

        for name, path in self._entries(ck_path, 'dataset', datasets, skip_patterns):
            r = self._import_dataset(name, path, ck_repo, to, desc.get('datasets') or {}, force, dry_run)
            if r['return'] > 0: return r
            report.append(('dataset', name, r['alias'], r['status']))

        for name, path in self._entries(ck_path, 'program', programs, skip_patterns):
            r = self._import_program(name, path, ck_repo, to, desc, force, dry_run)
            if r['return'] > 0: return r
            report.append(('program', name, r['alias'], r['status']))

        if licenses_md and not dry_run:
            r = self._licenses_md(to, desc)
            if r['return'] > 0: return r
            if con:
                print (f'cMeta info: {r["path"]} written ({r["programs"]} programs)')

        if con:
            print ('')
            for kind, name, alias, status in report:
                print (f'{kind:8} {name:44} -> {alias:52} {status}')
            print ('')
            print (f'cMeta info: {len(report)} CK entries looked at, {sum(1 for x in report if x[3].startswith("made"))} made')

        return {'return': 0, 'report': [{'kind': k, 'ck': n, 'alias': a, 'status': s} for k, n, a, s in report]}

    ############################################################
    def _ck_repo_name(self, ck_path):
        """The CK repository's name from its .ckr.json, else the folder's name."""
        ckr = os.path.join(ck_path, '.ckr.json')
        if os.path.isfile(ckr):
            try:
                with open(ckr, encoding = 'utf-8') as f:
                    d = json.load(f)
                url = (d.get('dict') or {}).get('url', '')
                return url.replace('https://github.com/', '').strip() or d.get('data_uoa') or os.path.basename(ck_path)
            except (OSError, ValueError):
                pass
        return os.path.basename(ck_path)

    def _entries(self, ck_path, module, patterns, skip_patterns):
        """(alias, folder) of the CK entries of a module whose alias matches the patterns."""
        if not patterns:
            return []
        folder = os.path.join(ck_path, module)
        if not os.path.isdir(folder):
            return []
        wanted = [p.strip() for p in patterns.split(',') if p.strip()]
        out = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(os.path.join(path, '.cm', 'meta.json')):
                continue
            if any(fnmatch.fnmatch(name, p) for p in wanted) and not any(fnmatch.fnmatch(name, s) for s in skip_patterns):
                out.append((name, path))
        return out

    def _load_json(self, path):
        with open(path, encoding = 'utf-8') as f:
            return json.load(f)

    def _ck_info(self, ck_folder, meta):
        """UID, date and description of a CK entry (.cm/info.json; the UID also in meta.json)."""
        info = {}
        fp = os.path.join(ck_folder, '.cm', 'info.json')
        if os.path.isfile(fp):
            try:
                info = self._load_json(fp)
            except (OSError, ValueError):
                info = {}
        uid = info.get('backup_data_uid') or meta.get('backup_data_uid') or ''
        date = ((info.get('control') or {}).get('iso_datetime') or '')[:10]
        return uid, date, info.get('description') or ''

    ############################################################
    def _find(self, category, alias):
        """The folders of the artifacts named alias, in every repository."""
        r = self.cm.access({'category': category, 'command': 'find', 'arg1': alias})
        if r['return'] > 0:
            return []
        return [a['path'] for a in r.get('artifacts', [])]

    def _create(self, category, to, alias, tags, yaml):
        """Make the artifact through the engine (its UID, generator and index), without a copyright key."""
        p = {'category': category, 'command': 'add', 'arg1': f'{to}:{alias}', 'quiet': True, 'con': False}
        if tags:
            p['tags'] = ','.join(tags)
        if yaml:
            p['yaml'] = True
        r = self.cm.access(p)
        if r['return'] > 0:
            return r
        paths = self._find(category, alias)
        repo_paths = [x for x in paths if os.sep + to + os.sep in x or '/' + to + '/' in x]
        if not repo_paths:
            return self.cm.error(f'"{alias}" was made but not found in repository "{to}"')
        return {'return': 0, 'path': repo_paths[0]}

    def _edit_cmeta(self, path, update):
        """Drop the copyright key and add keys to an artifact's _cmeta (json or yaml)."""
        for fn in ('_cmeta.json', '_cmeta.yaml'):
            fp = os.path.join(path, fn)
            if os.path.isfile(fp):
                break
        else:
            return self.cm.error(f'no _cmeta in "{path}"')

        r = self.cm.utils.files.read_file(fp)
        if r['return'] > 0: return r
        meta = r['data']
        meta.pop('copyright', None)
        meta.update(update)

        if fp.endswith('.json'):
            with open(fp, 'w', encoding = 'utf-8', newline = '\n') as f:
                json.dump(meta, f, indent = 2, sort_keys = True)
                f.write('\n')
        else:
            r = self.cm.utils.files.safe_write_file(fp, meta)
            if r['return'] > 0: return r
        return {'return': 0}

    def _reindex(self, category, alias):
        return self.cm.access({'category': category, 'command': 'reindex', 'arg1': alias, 'con': False})

    def _prepare_folder(self, category, alias, to, tags, yaml, force, dry_run):
        """An existing artifact is kept (or rewritten with --force when it is in "to"); else a new one."""
        existing = self._find(category, alias)
        mine = [x for x in existing if (os.sep + to + os.sep) in x]
        if existing and not (force and mine):
            where = existing[0]
            return {'return': 0, 'skip': True, 'status': f'exists ({where})'}
        if dry_run:
            return {'return': 0, 'skip': True, 'status': 'would be made'}
        if mine:
            return {'return': 0, 'path': mine[0], 'status': 'made again (--force)'}
        r = self._create(category, to, alias, tags, yaml)
        if r['return'] > 0: return r
        return {'return': 0, 'path': r['path'], 'status': 'made'}

    ############################################################
    def _import_dataset(self, name, ck_folder, ck_repo, to, cfg, force, dry_run):
        meta = self._load_json(os.path.join(ck_folder, '.cm', 'meta.json'))
        category = self.cmeta['uses_categories']['dataset']

        alias = cfg.get('alias_prefix', 'ctuning-') + name
        drop = set(cfg.get('drop_tags') or [])
        tags = list(cfg.get('add_tags') or [])
        for t in meta.get('tags') or []:
            if t and t not in drop and t not in tags:
                tags.append(t)

        r = self._prepare_folder(category, alias, to, tags, True, force, dry_run)
        if r['return'] > 0 or r.get('skip'):
            r.update({'return': r['return'], 'alias': alias})
            return r
        path = r['path']
        status = r['status']

        # Data into files/, the dataset's notices at its root
        files_dir = os.path.join(path, 'files')
        os.makedirs(files_dir, exist_ok = True)
        data_files = []
        for f in sorted(os.listdir(ck_folder)):
            src = os.path.join(ck_folder, f)
            if f == '.cm' or not os.path.isfile(src):
                continue
            if f.lower().startswith(DOC_FILES):
                shutil.copy2(src, os.path.join(path, f))
            else:
                shutil.copy2(src, os.path.join(files_dir, f))
                data_files.append(f)

        # A dataset that is a number (CK: run_cmd_main.dataset_number)
        props = meta.get('cm_properties') or {}
        number = ((props.get('run_time') or {}).get('run_cmd_main') or {}).get('dataset_number')
        if number is not None and not data_files:
            with open(os.path.join(files_dir, 'number.txt'), 'w', encoding = 'utf-8', newline = '\n') as f:
                f.write(str(number) + '\n')
            data_files.append('number.txt')

        # The order of the files: CK's dataset_files first (the first is what a program gets)
        order = [f for f in (meta.get('dataset_files') or []) if f in data_files]
        order += [f for f in data_files if f not in order]

        lines = ['authors: Grigori Fursin',
                 f'description: {q("cBench input " + name + " (cTuning MiDataSets), converted from the CK dataset " + name + ".")}',
                 '',
                 '# The files of the dataset in CK\'s order: the first is what a program gets by default.',
                 'files:']
        lines += [f'  - {q(f)}' for f in order]
        if props:
            lines += ['', '# Properties recorded in CK (cm_properties).',
                      'ck_properties: ' + json.dumps(props, sort_keys = True)]
        uid, date, ck_desc = self._ck_info(ck_folder, meta)
        lines += ['', 'origin:',
                  f'  ck_repo: {q(ck_repo)}',
                  f'  ck_entry: {q("dataset:" + name)}',
                  f'  ck_uid: {q(uid)}',
                  f'  ck_created: {q(date)}',
                  f'  ck_description: {q(ck_desc)}',
                  f'  converted: {q(datetime.date.today().isoformat() + " by task::import-ck")}',
                  '']
        with open(os.path.join(path, '_desc.yaml'), 'w', encoding = 'utf-8', newline = '\n') as f:
            f.write('\n'.join(lines))

        r = self._edit_cmeta(path, {'desc': f'cBench input {name} (cTuning MiDataSets): {", ".join(order)}.'})
        if r['return'] > 0: return r
        r = self._reindex(category, alias)
        if r['return'] > 0: return r

        return {'return': 0, 'alias': alias, 'status': status}

    ############################################################
    def _import_midatasets(self, patterns, skip_patterns, to, cfg, force, dry_run):
        """
        A dataset artifact per entry of the cTuning MiDataSets capsules (the index of task::get-ctuning-dataset):
        no files of its own - its _desc.yaml asks get-ctuning-dataset for them (uses + result_from_ctx), so the
        capsule is downloaded the first time one of its inputs is used. An artifact that exists is kept
        (the small inputs with their files, in this repository or another); --force remakes those of "to"
        that have no files of their own.
        """
        r = self.cm.access({'category': 'task', 'command': 'find', 'arg1': 'get-ctuning-dataset', 'con': False})
        if r['return'] > 0: return r
        if not r.get('artifacts'):
            return self.cm.error('task::get-ctuning-dataset not found')
        task_path = r['artifacts'][0]['path']
        rr = self.cm.utils.files.read_file(os.path.join(task_path, '_cmeta.yaml'))
        if rr['return'] > 0: return rr
        task_uid = rr['data'].get('artifact') or ''
        rr = self.cm.utils.files.read_file(os.path.join(task_path, '_desc.yaml'))
        if rr['return'] > 0: return rr
        indexes = []
        for ix in rr['data'].get('indexes') or []:
            index_path = os.path.join(task_path, ix.get('index') or '')
            try:
                with open(index_path, encoding = 'utf-8') as f:
                    indexes.append(json.load(f))
            except (OSError, ValueError) as e:
                return self.cm.error(f'the index "{index_path}" cannot be read: {e}')

        category = self.cmeta['uses_categories']['dataset']
        wanted = [p.strip() for p in patterns.split(',') if p.strip()]
        report = []

        # Every set of capsules: the MiDataSets (cBench inputs), the office snapshots of the CK paper ...
        # A set says its tags ("tags" of its index); the MiDataSets have those of the cBench inputs
        pairs = [(index, kind, rec) for index in indexes for kind, rec in sorted(index['capsules'].items())]
        for index, kind, rec in pairs:
            set_tags = index.get('tags') or (list(cfg.get('add_tags') or []) + ['midatasets'])
            office = 'ck-paper' in set_tags
            what = 'CK paper input' if office else 'cBench input'
            source = 'the office webcam snapshots of the CK paper repository' if office else 'cTuning MiDataSets'
            for entry, x in sorted(rec['entries'].items()):
                if not any(fnmatch.fnmatch(entry, p) for p in wanted) or any(fnmatch.fnmatch(entry, s) for s in skip_patterns):
                    continue
                alias = cfg.get('alias_prefix', 'ctuning-') + entry

                existing = self._find(category, alias)
                own_files = [p for p in existing if os.path.isdir(os.path.join(p, 'files'))]
                if own_files:
                    report.append(('dataset', entry, alias, f'exists with its files ({own_files[0]})'))
                    continue

                tags = list(set_tags)
                for t in x.get('tags') or []:
                    if t and t not in tags and t not in (cfg.get('drop_tags') or []):
                        tags.append(t)

                r = self._prepare_folder(category, alias, to, tags, True, force, dry_run)
                if r['return'] > 0: return r
                if r.get('skip'):
                    report.append(('dataset', entry, alias, r['status']))
                    continue
                path = r['path']
                status = r['status']

                files = list(x.get('order') or [f['name'] for f in x['files']])
                lines = ['authors: Grigori Fursin',
                         'description: ' + q(f'{what} {entry} ({source}), from the capsule {rec["capsule"]}, '
                                             'downloaded on demand by task::get-ctuning-dataset.'),
                         '',
                         f'# The files come from a capsule of {source}, unpacked once into the cache',
                         'uses:',
                         f'  - task: get-ctuning-dataset,{task_uid}',
                         f'    capsule: {q(kind)}',
                         f'    entry: {q(entry)}',
                         "result_from_ctx: '{{global.get-ctuning-dataset}}'",
                         '',
                         "# The files of the dataset in CK's order: the first is what a program gets by default.",
                         'files:']
                lines += [f'  - {q(f)}' for f in files]
                if x.get('number') is not None:
                    lines += ['', '# The number a program takes (CK: run_cmd_main.dataset_number), also in number.txt',
                              f'number: {q(x["number"])}']
                lines += ['', 'origin:',
                          f'  ck_repo: {q(x.get("ck_repo") or "ctuning-datasets")}',
                          f'  ck_entry: {q("dataset:" + entry)}',
                          f'  ck_uid: {q(x.get("ck_uid") or "")}',
                          f'  ck_created: {q(x.get("ck_created") or "")}',
                          f'  capsule: {q(rec["capsule"])}',
                          f'  converted: {q(datetime.date.today().isoformat() + " by task::import-ck")}',
                          '']
                with open(os.path.join(path, '_desc.yaml'), 'w', encoding = 'utf-8', newline = '\n') as f:
                    f.write('\n'.join(lines))

                r = self._edit_cmeta(path, {'desc': f'{what} {entry} ({source}, on demand): {", ".join(files)}.'})
                if r['return'] > 0: return r
                r = self._reindex(category, alias)
                if r['return'] > 0: return r
                report.append(('dataset', entry, alias, status))

        return {'return': 0, 'report': report}

    ############################################################
    def _import_program(self, name, ck_folder, ck_repo, to, desc, force, dry_run):
        meta = self._load_json(os.path.join(ck_folder, '.cm', 'meta.json'))
        category = self.cmeta['uses_categories']['program']

        family = None
        for prefix, fam in (desc.get('families') or {}).items():
            if name.startswith(prefix):
                family = fam
                short = name[len(prefix):]
                break
        if family is None:
            return {'return': 0, 'alias': name, 'status': 'skipped (no family for this CK program)'}

        override = (desc.get('programs') or {}).get(name) or {}
        tags = [t for t in (meta.get('tags') or []) if t and t != 'program']

        r = self._prepare_folder(category, name, to, tags, False, force, dry_run)
        if r['return'] > 0 or r.get('skip'):
            r.update({'return': r['return'], 'alias': name})
            return r
        path = r['path']
        status = r['status']

        # The sources and every other file of the CK entry (headers, data tables, key rings, LICENSE)
        src_dir = os.path.join(path, 'src')
        if os.path.isdir(src_dir) and force:
            shutil.rmtree(src_dir)
        os.makedirs(src_dir, exist_ok = True)
        for f in sorted(os.listdir(ck_folder)):
            src = os.path.join(ck_folder, f)
            if f == '.cm' or f.startswith('tmp') or f == '__pycache__':
                continue
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(src_dir, f))
            else:
                shutil.copy2(src, os.path.join(src_dir, f))

        # The changes to CK's sources: the family's, then the program's own patch
        r = self._patch_sources(name, family, meta, src_dir)
        if r['return'] > 0: return r
        patches = r['patches']

        # The licence files the CK entry lacks
        licenses = desc.get('licenses') or {}
        for target, source in {**(licenses.get(family) or {}), **(licenses.get(name) or {})}.items():
            dst = os.path.join(src_dir, target)
            if not os.path.exists(dst):
                shutil.copy2(os.path.join(self.artifact_path, 'files', 'licenses', source), dst)

        commands = self._commands(name, meta, override)
        if isinstance(commands, dict) and commands.get('return'):
            return commands

        text = self._program_desc(name, short, family, meta, override, commands, ck_repo, ck_folder, patches)
        with open(os.path.join(path, '_desc.yaml'), 'w', encoding = 'utf-8', newline = '\n') as f:
            f.write(text)

        # The hooks come from template-ck-program of cmeta-aops (inherited): no copy of them here
        for old in ('api_v1.py', '__pycache__'):
            x = os.path.join(path, old)
            if os.path.isfile(x):
                os.remove(x)
            elif os.path.isdir(x):
                shutil.rmtree(x)

        with open(os.path.join(path, 'README.md'), 'w', encoding = 'utf-8', newline = '\n') as f:
            f.write(self._program_readme(name, family, meta, override, commands, ck_repo, patches))

        computes = self._computes(family, desc)
        for compute in computes:
            tmp = '' if compute == 'cpu' else f' --target_tmp=tmp-{compute}'
            tests = [f'cx program run {name} --compute={compute}{tmp}' + (f' --cmd={c}' if len(commands) > 1 else '') + ' -q'
                     for c in commands]
            with open(os.path.join(path, f'_test_{compute.replace("-cpu", "") if compute != "cpu" else "cpu"}.bat'),
                      'w', encoding = 'utf-8', newline = '\r\n') as f:
                f.write('\n'.join(tests) + '\n')

        x = SUITES.get(family, family)
        update = {'constraints': {'supported_compute': computes},
                  'desc': f'{x}: {short}, converted from the CK program {name}.'}
        r = self._edit_cmeta(path, update)
        if r['return'] > 0: return r
        r = self._reindex(category, name)
        if r['return'] > 0: return r

        return {'return': 0, 'alias': name, 'status': status}

    def _license_info(self, name, family):
        """The licence of a program's sources: licenses_info of _desc.yaml, by program, else by family."""
        desc = self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {}
        info = desc.get('licenses_info') or {}
        return info.get(name) or info.get(family) or {}

    def _licenses_md(self, to, desc):
        """LICENSES.md at the root of the repository: the licence of every program, dataset, task and note."""
        r = self.cm.access({'category': 'repo', 'command': 'find', 'arg1': to, 'con': False})
        if r['return'] > 0: return r
        repos = r.get('artifacts') or r.get('repos') or []
        root = repos[0]['path'] if repos and isinstance(repos[0], dict) else (repos[0] if repos else None)
        if not root or not os.path.isdir(root):
            return self.cm.error(f'repository "{to}" not found')

        rows = []
        for kind in ('program',):
            folder = os.path.join(root, kind)
            for a in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
                fp = os.path.join(folder, a, '_desc.yaml')
                if not os.path.isfile(fp):
                    continue
                rr = self.cm.utils.files.read_file(fp)
                data = (rr.get('data') or {}) if rr['return'] == 0 else {}
                lic = data.get('license') or {}
                suite = (data.get('origin') or {}).get('suite') or ''
                rows.append((a, suite, lic.get('spdx') or '', lic.get('name') or 'not recorded', lic.get('file') or ''))

        datasets = os.path.join(root, 'dataset')
        n_local = n_capsule = n_office = 0
        for a in os.listdir(datasets) if os.path.isdir(datasets) else []:
            if os.path.isdir(os.path.join(datasets, a, 'files')):
                n_local += 1
            elif os.path.isfile(os.path.join(datasets, a, '_desc.yaml')):
                rr = self.cm.utils.files.read_file(os.path.join(datasets, a, '_cmeta.yaml'))
                tags = ((rr.get('data') or {}).get('tags') or []) if rr['return'] == 0 else []
                if 'ck-paper' in tags:
                    n_office += 1
                else:
                    n_capsule += 1

        suites = []
        for _, suite, _, _, _ in rows:
            if suite not in suites:
                suites.append(suite)

        L = ['# Licences of the artifacts of this repository', '',
             'Generated by `cx task run import-ck --licenses_md` from the `license` block of every program\'s',
             '`_desc.yaml` (do not edit by hand: change `licenses_info` in `task/import-ck/_desc.yaml`).', '',
             '## What is Apache-2.0', '',
             'Everything this repository adds (`LICENSE`): the cMeta descriptions (`_cmeta.*`, `_desc.yaml`, `README.md`',
             'of every artifact), the tasks (`task/*`), the notes (`note/*`) and the patches of `task/import-ck/files/patches/`',
             'as changes (the patched sources stay under the licence of the program). The hooks of the converted',
             'programs are `template-ck-program` of cmeta-aops (Apache-2.0).', '',
             '## Programs: the licence of their sources (`src/`)', '',
             'An SPDX identifier when the text is one of the SPDX list; otherwise the licence is named. The text is',
             'in the file named, in the program\'s folder.', '']
        for suite in suites:
            L += [f'### {suite or "Other"}', '', '| Program | Licence | SPDX | Text |', '|---|---|---|---|']
            for a, s_, spdx, name, file in rows:
                if s_ == suite:
                    L.append(f'| `program/{a}` | {name} | {("`" + spdx + "`") if spdx else "-"} | {("`" + file + "`") if file else "-"} |')
            L.append('')
        L += ['## Datasets', '',
              f'- {n_local} datasets with their files (`dataset/ctuning-*` with a `files/` folder): the small inputs of',
              '  cBench (CK `ctuning-datasets-min`); their origins and licences were not recorded in CK.',
              f'- {n_capsule} datasets fetched on demand (`dataset/ctuning-*` without files): the cTuning MiDataSets',
              '  (CK `ctuning-datasets`), from the capsules of their Zenodo record, under the licence of that record',
              '  (see the README of the capsules for their provenance).',
              f'- {n_office} datasets fetched on demand (`dataset/ctuning-*fgg-office*`): the webcam snapshots of',
              '  Grigori Fursin\'s office, by day and night, of the CK paper repository (`reproduce-ck-paper`,',
              '  BSD-3-Clause), from their own capsule.', '',
              '## Binary capsules', '',
              'The MILEPOST GCC capsules that `task/extract-milepost-features-legacy` downloads are in the Zenodo record',
              '10.5281/zenodo.24246695, each with its licences (GPL-3.0-or-later, GPL-2.0-only, LGPL ...; see its README).', '']

        path = os.path.join(root, 'LICENSES.md')
        with open(path, 'w', encoding = 'utf-8', newline = '\n') as f:
            f.write('\n'.join(L))
        return {'return': 0, 'path': path, 'programs': len(rows)}

    def _computes(self, family, desc):
        """The targets the programs of a family declare (supported_compute of _desc.yaml, by family)."""
        x = desc.get('supported_compute') or ['cpu']
        if isinstance(x, dict):
            x = x.get(family) or x.get('default') or ['cpu']
        return sorted(x)

    ############################################################
    def _patch_sources(self, name, family, meta, src_dir):
        """
        Change CK's sources where they would not build or run on every target. Returns the list of
        the changes, one line each, for the program's _desc.yaml and README.
        """
        patches = []

        if family == 'polybench':
            for f in sorted(os.listdir(src_dir)):
                if not f.endswith('.h'):
                    continue
                fp = os.path.join(src_dir, f)
                text, encoding, newline = read_text(fp)
                if POLYBENCH_FORMAT_BLOCK.search(text):
                    write_text(fp, POLYBENCH_FORMAT_BLOCK.sub(lambda m: POLYBENCH_FORMAT, text, count = 1), encoding, newline)
                    patches.append(f'{f}: the printf format of DATA_TYPE by token pasting (MSVC refuses "#if DATA_TYPE == double")')

            for f in meta.get('source_files') or []:
                fp = os.path.join(src_dir, f)
                text, encoding, newline = read_text(fp)
                new = self._polybench_dump_to_file(text)
                if new is None:
                    return self.cm.error(f'CK program "{name}": no print_array function found in "{f}"')
                write_text(fp, new, encoding, newline)
                patches.append(f'{f}: print_array writes the arrays into {POLYBENCH_DUMP_FILE} (not the standard streams)')

        if family == 'polybench-cuda':
            # CUDA 13 removed cudaDeviceProp::computeMode and cudaThreadSynchronize (deprecated since CUDA 4):
            # a block in front of GPU_argv_init() (the first function that uses either) maps them to the
            # current calls from CUDA 13 on and keeps the original ones for CUDA 11 and 12
            for f in meta.get('source_files') or []:
                fp = os.path.join(src_dir, f)
                text, encoding, newline = read_text(fp)
                old_check = 'if (deviceProp.computeMode == cudaComputeModeProhibited)'
                if 'void GPU_argv_init()' not in text or old_check not in text:
                    continue
                first_use = min(i for i in (text.find('cudaThreadSynchronize'), text.find(old_check)) if i >= 0)
                if text.find('void GPU_argv_init()') > first_use:
                    return self.cm.error(f'CK program "{name}": "{f}" uses cudaThreadSynchronize or computeMode before GPU_argv_init()')
                new = text.replace(old_check, 'if (ck_compute_mode_prohibited(gpgpu_device_id, &deviceProp))')
                new = new.replace('void GPU_argv_init()', CUDA_COMPAT + 'void GPU_argv_init()', 1)
                write_text(fp, new, encoding, newline)
                patches.append(f'{f}: from CUDA 13 on (CUDART_VERSION >= 13000) cudaDeviceSynchronize() for cudaThreadSynchronize() '
                               'and the compute mode from cudaDeviceGetAttribute - CUDA 13 removed both; CUDA 11 and 12 keep the original calls')

        if family == 'polybench-opencl':
            # The arrays of platform and device IDs had sizeof(id) * index + 1 BYTES (1 byte for index 0),
            # while clGetPlatformIDs and clGetDeviceIDs write up to 15 IDs into them: a heap overflow on a
            # machine with two OpenCL platforms or devices or more
            for f in meta.get('source_files') or []:
                fp = os.path.join(src_dir, f)
                text, encoding, newline = read_text(fp)
                new = text
                for kind, index in (('cl_platform_id', 'gpgpu_platform_id'), ('cl_device_id', 'gpgpu_device_id')):
                    old = f'malloc(sizeof({kind}) * {index}+1)'
                    if new.count(old) == 1:
                        new = new.replace(old, f'malloc(sizeof({kind}) * ({index} + 15))  /* cMeta: room for the 15 IDs asked for '
                                               f'(was sizeof * {index} + 1 bytes) */')
                if new != text:
                    write_text(fp, new, encoding, newline)
                    patches.append(f'{f}: the arrays of OpenCL platform and device IDs hold the 15 IDs clGetPlatformIDs and '
                                   'clGetDeviceIDs may write (they had sizeof(id) * index + 1 bytes: a heap overflow with two '
                                   'platforms or devices or more)')

        if family in ('polybench-cuda', 'polybench-opencl'):
            # The CK versions commented out the CPU reference of main() (the block with the CPU kernel's timer,
            # xopenme_clock_start(1)): their "Non-Matching CPU-GPU Outputs" count compared the GPU's result with
            # memory never computed. The block is compiled with CK_CPU_CHECK (the hooks define it unless
            # --compile.check=no), so that the count is a check; the same lines, the comment's two made directives
            for f in meta.get('source_files') or []:
                fp = os.path.join(src_dir, f)
                text, encoding, newline = read_text(fp)

                # The kernels of 3mm, atax, bicg and gesummv add (+=) into arrays that main() sends to the GPU
                # without initializing them: their result depended on what the memory held (often zero by luck)
                text, n = zeroed_arrays(text)
                if n < 0:
                    return self.cm.error(f'CK program "{name}": an array of main() in "{f}" is not allocated as '
                                         '(DATA_TYPE*)malloc(<n>*sizeof(DATA_TYPE))')
                if n:
                    patches.append(f'{f}: the arrays of main() are allocated zeroed (calloc): kernels that add into an '
                                   'array main() sends to the GPU uninitialized (3mm, atax, bicg, gesummv) gave results '
                                   'that depended on what the memory held')

                new, n = cpu_check_block(text)
                if n != 1:
                    return self.cm.error(f'CK program "{name}": {n} commented CPU reference blocks in main() of "{f}" (1 expected)')
                write_text(fp, new, encoding, newline)
                patches.append(f'{f}: the CPU reference of main() that CK commented out is compiled with CK_CPU_CHECK (defined '
                               'unless --compile.check=no), so that "Non-Matching CPU-GPU Outputs" compares the GPU\'s result '
                               'with the CPU\'s')

        patch = os.path.join(self.artifact_path, 'files', 'patches', name + '.patch')
        if os.path.isfile(patch):
            with open(patch, encoding = 'utf-8') as f:
                try:
                    description, files = parse_patch(f.read())
                except ValueError as e:
                    return self.cm.error(f'patch "{patch}": {e}')
            for fname, hunks in files:
                fp = os.path.join(src_dir, fname)
                if not os.path.isfile(fp):
                    return self.cm.error(f'patch "{patch}": no file "{fname}" in the sources of "{name}"')
                text, encoding, newline = read_text(fp)
                lines = apply_hunks(text.split('\n'), hunks)
                if lines is None:
                    return self.cm.error(f'patch "{patch}" does not apply to "{fname}" (CK\'s source changed?)')
                write_text(fp, '\n'.join(lines), encoding, newline)
            patches += description or [f'files/patches/{name}.patch of task::import-ck']

        return {'return': 0, 'patches': patches}

    def _polybench_dump_to_file(self, text):
        """print_array of a PolyBench kernel writing into the dump file: None when there is none."""
        m = re.search(r'\n(static\s*\n)?void print_array\(', text)
        if not m:
            return None
        opening = text.find('\n{', m.end())
        if opening < 0:
            return None
        depth, k = 0, opening + 1
        while k < len(text):
            if text[k] == '{':
                depth += 1
            elif text[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        else:
            return None

        body = text[opening + 2:k]          # between "{" and the closing "}"
        body = re.sub(r'\bfprintf\s*\(\s*stderr\s*,', 'fprintf (ck_dump,', body)
        body = re.sub(r'(?<![\w])printf\s*\(', 'fprintf (ck_dump, ', body)
        body = '\n  FILE *ck_dump = ck_dump_open ();' + body.rstrip() + '\n\n  ck_dump_close (ck_dump);\n'

        # The helpers go before print_array and the comment just above it
        start = m.start() + 1
        before = text[:start].rstrip()
        if before.endswith('*/'):
            c = before.rfind('/*')
            if c >= 0:
                start = before.rfind('\n', 0, c) + 1
        return text[:start] + POLYBENCH_DUMP_HELPERS + text[start:opening + 2] + body + text[k:]

    ############################################################
    def _commands(self, name, meta, override):
        """The commands of a CK program: CK's run_cmds, translated, with the overrides applied."""
        out = {}
        over = override.get('commands') or {}

        for cmd, v in (meta.get('run_cmds') or {}).items():
            rt = v.get('run_time') or {}
            o = over.get(cmd) or {}

            main = rt.get('run_cmd_main') or ''
            main = main.replace('$#BIN_FILE#$', '').strip()
            main = main.replace('$#dataset_path#$$#dataset_filename#$', '{qinput_files.data}')
            for n in range(1, 4):
                main = main.replace(f'$#dataset_path#$$#dataset_filename_{n}#$', '{qinput_files.data' + str(n) + '}')
            main = main.replace('$#dataset_number#$', '{{local.ck_number}}')
            # A file of the program's sources (PolyBench/GPU OpenCL: its kernel): run from the run folder,
            # where the hooks copy it (host) or push it (device) - ck_run_files
            run_files = re.findall(r'"?\$#src_path#\$([^"\s]+)"?', main)
            main = re.sub(r'"?\$#src_path#\$([^"\s]+)"?', r'\1', main)
            if 'cmd_main' in o:
                main = o['cmd_main']
            if '$#' in main or '<' in main:
                return self.cm.error(f'CK program "{name}", command "{cmd}": "{main}" needs an override (cmd_main)')

            tags = [t for t in (v.get('dataset_tags') or []) if t and t != 'dataset']
            if 'dataset_tags' in o:
                tags = [t for t in o['dataset_tags'].split(',') if t]
            uses_dataset = bool(v.get('dataset_tags')) or 'dataset_tags' in o
            if uses_dataset and not tags:
                return self.cm.error(f'CK program "{name}", command "{cmd}" took any dataset: give its dataset_tags in the overrides')

            outputs = [f for f in (rt.get('run_output_files') or [])
                       if f not in ('tmp-output1.tmp', 'tmp-output2.tmp', 'tmp-ck-timer.json')]
            if 'output_files' in o:
                outputs = list(o['output_files'])

            out[cmd] = {'main': main,
                        'run_files': run_files,
                        'dataset_tags': ','.join(tags) if uses_dataset else None,
                        'dataset_file': o.get('dataset_file'),
                        'input_files': o.get('input_files', True) and uses_dataset,
                        'outputs': outputs,
                        'hot_functions': [h.get('name') for h in v.get('hot_functions') or [] if h.get('name')]}
        return out

    ############################################################
    def _dataset_step(self, c, indent):
        s = ' ' * indent
        x = [f'{s}- task: {TASK_DATASET}',
             f'{s}  dataset_tags: {c["dataset_tags"]}',
             f"{s}  name: '{{{{params.dataset|$None}}}}'"]
        default = '$None' if not c['dataset_file'] else c['dataset_file']
        x.append(f"{s}  filename: '{{{{params.dataset_file|{default}}}}}'")
        return x

    def _program_desc(self, name, short, family, meta, override, commands, ck_repo, ck_folder, patches):
        cmds = list(commands)
        first = commands[cmds[0]]
        multi = len(cmds) > 1
        any_dataset = any(c['dataset_tags'] for c in commands.values())
        ck_vars = meta.get('build_compiler_vars') or {}

        L = ['authors: Grigori Fursin',
             'inherits:',
             f'  - {TEMPLATE}',
             f'  - {TEMPLATE_CK}       # the hooks of converted programs (cmeta-aops)',
             '',
             '# Converted from the Collective Knowledge (CK) format by task::import-ck; see README.md.',
             'origin:',
             f'  suite: {q(SUITES.get(family, family))}',
             f'  ck_repo: {q(ck_repo)}',
             f'  ck_entry: {q("program:" + name)}',
             f'  ck_uid: {q(self._ck_info(ck_folder, meta)[0])}',
             f'  ck_created: {q(self._ck_info(ck_folder, meta)[1])}',
             f'  converted: {q(datetime.date.today().isoformat() + " by task::import-ck")}']
        if patches:
            L += ['  # What was changed in the CK sources, and why', '  patches:']
            L += [f'    - {q(p)}' for p in patches]
        info = self._license_info(name, family)
        if info:
            L += ['', '# The licence of the sources (the cMeta description and hooks: Apache-2.0)', 'license:',
                  f'  name: {q(info.get("name") or "")}']
            if info.get('spdx'):
                L.append(f'  spdx: {q(info["spdx"])}')
            if info.get('file'):
                L.append(f'  file: {q(info["file"])}')
        cuda = family == 'polybench-cuda'
        opencl = family == 'polybench-opencl'
        L += ['',
             '#' * 99,
             'local_vars:',
             '  lang: cuda' if cuda else '  lang: c',
             '',
             '  src_file_names:']
        L += [f'    - {q(f)}' for f in meta.get('source_files') or []]
        L += ['', f'  target_file_name: {q(short)}', '']

        if first['input_files'] and not multi or (multi and any(c['input_files'] for c in commands.values())):
            L += ['  input_files:', "    data: '{{local.dataset.path}}'", '']

        timers = 'XOPENME' in ck_vars
        base_outputs = (['tmp-ck-timer.json'] if timers else []) + ([] if multi else first['outputs'])
        L += ['  output_files:'] + [f'    - {q(f)}' for f in base_outputs]
        if timers:
            L += ['', '  result_files:', '    stats-xopenme: tmp-ck-timer.json']
        L += ['',
              '  run_time_env:',
              "    CMETA_TARGETS: '{{global.target.cmeta_targets}}'",
              "    CT_REPEAT_MAIN: '{{local.params.repeat|1}}'"]
        for k, v in (override.get('run_time_env') or {}).items():
            L.append(f'    {k}: {q(v)}')
        L += ['',
              '  # Hooks of template-ck-program (customize_ck_run): standard output and error into files, as CK did',
              '  ck_redirect_stdio: True']
        run_files = sorted({f for c in commands.values() for f in c.get('run_files') or []})
        if run_files and 'ck_run_files' not in (override.get('local_vars') or {}):
            L += ['', '  # Files of src/ the run reads from its folder (copied there, pushed to a device)',
                  '  ck_run_files: ' + json.dumps(run_files)]
        if opencl:
            L += ['', '  # The OpenCL platform and device (CK_COMPUTE_PLATFORM_ID, CK_COMPUTE_DEVICE_ID): --opencl_platform,',
                  '  # --opencl_device=<number or a word of its name>, else the first GPU the opencl target found',
                  '  ck_opencl_device: True']
        if family in ('polybench-cuda', 'polybench-opencl'):
            L += ['', '  # The CPU reference of main(), a comment in the CK version: CK_CPU_CHECK (the hooks), so that',
                  '  # "Non-Matching CPU-GPU Outputs" is a check; --compile.check=no leaves it out, as CK did',
                  '  ck_cpu_check: True']
        for k, v in (override.get('local_vars') or {}).items():
            L.append(f'  {k}: ' + json.dumps(v))
        if family == 'polybench':
            sizes = [k for k in ck_vars if k not in POLYBENCH_NOT_SIZES]
            L += ['',
                  '  # PolyBench (hooks of template-ck-program): CK\'s sizes, replaced by the header\'s with --compile.size=<mini|',
                  '  # small|standard|large|extralarge>; the arrays dumped into this file (--compile.dump=yes|no)',
                  '  ck_size_vars: ' + json.dumps(sizes),
                  f'  ck_dump_file: {POLYBENCH_DUMP_FILE}']
        hot = {c: v['hot_functions'] for c, v in commands.items() if v['hot_functions']}
        if hot:
            L += ['', '  # Where CK measured the time goes (hot_functions)', '  ck_hot_functions:']
            for c, fs in hot.items():
                L.append(f'    {c}: ' + json.dumps(fs))

        # Compile: the defines CK passed (PolyBench: its small sizes and the dump of the arrays, which
        # the hooks change with --compile.size and --compile.dump), libm, the run-time libraries
        L += ['', '#' * 99, 'params:']
        if cuda:
            L += ['  compute: cuda']
        elif opencl:
            L += ['  compute: opencl']
        L += ['  compile:', '    d:' if ck_vars else '    d: {}']
        for k, v in ck_vars.items():
            L.append(f'      {k}:' + ('' if v == '' or v is None else f' {q(v)}'))
        if opencl:
            L += ["      # The OpenCL API these codes use (1.2): the Khronos headers would default to 3.0 and warn",
                  "      CL_TARGET_OPENCL_VERSION: '120'"]
        if '$<<CK_EXTRA_LIB_M>>$' in (meta.get('extra_ld_vars') or ''):
            L += ['', 'params_os:', '  linux:', '    compile:', '      lib_names:', '        - m']
        if cuda:
            L += ['', '# nvcc builds for the architecture of the GPU it finds', 'use:', '  nvcc:', '    with:',
                  '      arch_flags: True']

        L += ['', '#' * 99, 'updates:', '  compile:', '    uses:',
              '      - match:', '          internal_func: customize2', '        append:',
              '          # The run-time libraries (built once per target and cached by task setup)']
        if family in ('polybench', 'polybench-cuda', 'polybench-opencl'):
            L += [f'          - task: {TASK_SETUP}', f'            name: {LIB_POLYBENCH}',
                  '            with:', "              static: '{{params.compile.static|$None}}'", '']
        if family != 'ck-codelet':
            L += [f'          - task: {TASK_SETUP}', f'            name: {LIB_XOPENME}',
                  '            with:', "              static: '{{params.compile.static|$None}}'", '']
        if cuda:
            L += ['          # The CUDA runtime: its library folder on the run-time path (a CUDA of the cMeta cache',
                  '          # is not on the system\'s)',
                  f'          - task: {TASK_SETUP}', f'            name: {LIB_CUDA}', '']
        elif opencl:
            L += ['          # The OpenCL headers and the library to link (Windows: OpenCL.lib; Linux: the ICD loader;',
                  '          # macOS: the OpenCL framework; Android: a stub of libOpenCL.so); the drivers bring the',
                  '          # OpenCL library a run loads (on Android the vendor\'s libOpenCL.so)',
                  f'          - task: {TASK_SETUP}',
                  "            if: '\"opencl\" in {{global.target.compute|$[]}} or \"android-gpu\" in {{global.target.compute|$[]}}'",
                  f'            name: {LIB_OPENCL}', '',
                  '          # Android (android-gpu): the libraries of the NDK sysroot',
                  f'          - task: {TASK_SETUP}',
                  "            if: '\"android-gpu\" in {{global.target.compute|$[]}}'",
                  f'            name: {LIB_SYSROOT_ANDROID}',
                  '            with:',
                  "              static: '{{local.params.compile.static|$None}}'",
                  '              lib_names:', '                - dl', '                - m', '']
        else:
            L += ['          # Android: the libraries of the NDK sysroot',
              f'          - task: {TASK_SETUP}',
              "            if: '\"android-cpu\" in {{global.target.compute|$[]}}'",
              f'            name: {LIB_SYSROOT_ANDROID}',
              '            with:',
              "              static: '{{local.params.compile.static|$None}}'",
              '              lib_names:', '                - dl', '                - m', '                - z',
              '              dynamic_libs:', '                - c++_shared', '']

        L += ['  run:', '    uses:', '      - match:', '          internal_func: customize_run', '        append:']
        if any_dataset:
            ds = first if first['dataset_tags'] else next(c for c in commands.values() if c['dataset_tags'])
            L += self._dataset_step(ds, 10) + ['']
        L += ['          - internal_func: customize_ck_run',
              '            internal_func_from_local_key: selected-program',
              '            internal_func_safe: True']
        if not multi:
            L += ['', '      - match:', f'          task: {TASK_SETUP_RUN}', '        update:',
                  f'          cmd_main: {q((first["main"] + " {{local.ck_redirects|}}").strip())}']

        if multi:
            L += ['', '#' * 99, '# The commands of the CK program (--cmd=<name>)', 'updates_cmd:']
            for c, v in commands.items():
                L += [f'  {c}:', '    run:', '      uses:']
                if v['dataset_tags']:
                    default = v['dataset_file'] or '$None'
                    L += ['        - match:', f'            task: {TASK_DATASET}', '          update:',
                          f'            dataset_tags: {v["dataset_tags"]}',
                          f"            filename: '{{{{params.dataset_file|{default}}}}}'"]
                L += ['        - match:', f'            task: {TASK_SETUP_RUN}', '          update:',
                      f'            cmd_main: {q((v["main"] + " {{local.ck_redirects|}}").strip())}']
                if v['outputs']:
                    L += ['    local_vars:', '      +output_files:'] + [f'        - {q(f)}' for f in v['outputs']]
                L.append('')

        return '\n'.join(L).rstrip() + '\n'

    ############################################################
    def _program_readme(self, name, family, meta, override, commands, ck_repo, patches):
        multi = len(commands) > 1
        ck_vars = meta.get('build_compiler_vars') or {}
        sizes = ', '.join(f'{k}={v}' for k, v in ck_vars.items() if k not in POLYBENCH_NOT_SIZES)
        libs = (['`lib-xopenme`'] if family != 'ck-codelet' else []) + \
               (['`lib-polybench`'] if family in ('polybench', 'polybench-cuda', 'polybench-opencl') else []) + \
               (['`lib-cuda`'] if family == 'polybench-cuda' else []) + \
               (['`lib-opencl`'] if family == 'polybench-opencl' else [])
        L = [f'# {name}', '',
             f'{SUITES.get(family, family)}: the CK program `{name}` of `{ck_repo}`, converted to cMeta by',
             '`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of',
             '`template-ck-program` (both in cmeta-aops)' + (' and uses the run-time libraries of cmeta-aops' if libs else '') +
             ('\n(' + ', '.join(libs) + ').' if libs else '.'),
             '', '## Run', '', '```bash']
        computes = self._computes(family, self.cdesc if isinstance(getattr(self, 'cdesc', None), dict) else {})
        for c, v in commands.items():
            x = f' --cmd={c}' if multi else ''
            L.append(f'cx program run {name} {computes[0] if "cpu" not in computes else "cpu"}{x} -q')
        for device in ('android-cpu', 'android-gpu'):
            if device in computes:
                L.append(f'cx program run {name} --compute={device} --target_tmp=tmp-{device}' +
                         (f' --cmd={list(commands)[0]}' if multi else '') + ' -q')
        L += ['```', '']
        if family == 'polybench-opencl':
            L += ['It runs the kernel (the `.cl` file, built by the OpenCL driver at run time) on an OpenCL device:',
                  'with `opencl`, the first GPU the `opencl` target finds, or `--opencl_device=<number or a word of',
                  'its name>` (with `--opencl_platform=<number>`), e.g. `--opencl_device=intel`; with `android-gpu`,',
                  'the GPU of the Android device (its own libOpenCL.so). It prints the platform and the device.', '']
        if family in ('polybench-cuda', 'polybench-opencl'):
            L += ['**The check:** the program computes the result on the CPU too and prints how many elements of the',
                  'GPU\'s result differ from it beyond the threshold of the source (`Non-Matching CPU-GPU Outputs',
                  'Beyond Error Threshold of <p> Percent: <n>`, on standard output; 0 is right). The CK version had',
                  'that CPU reference in a comment (so its count compared with memory never computed);',
                  '`--compile.check=no` builds it so again. The sizes are CK\'s (compile variables).', '']
        if family == 'polybench-cuda':
            L += ['It runs the kernel on the GPU (`cuda`), with CUDA 11, 12 or 13 (`--use.nvcc.version=<v>`); the GPU',
                  'and its compute capability are printed first.', '']
        if any(v['dataset_tags'] for v in commands.values()):
            L += ['The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):',
                  '`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.', '',
                  '| Command | Dataset tags | File | Command line after the executable |',
                  '|---|---|---|---|']
            for c, v in commands.items():
                L.append(f'| `{c}` | `{v["dataset_tags"] or "-"}` | `{v["dataset_file"] or "(the first)"}` | `{v["main"]}` |')
            L.append('')
        if family == 'polybench':
            L += [f'Sizes: CK\'s by default ({sizes}), with the arrays dumped into `{POLYBENCH_DUMP_FILE}`',
                  '(the result to compare between targets). `--compile.size=mini|small|standard|large|extralarge`',
                  'takes the sizes of PolyBench\'s header instead, without the dump unless `--compile.dump=yes`;',
                  '`--compile.dump=no` leaves the dump out. Each choice is a build of its own.', '',
                  '```bash',
                  f'cx program run {name} cpu --compile.size=large -q',
                  '```', '']
        L += ['`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to',
              '`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the',
              'kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).', '']
        if (override.get('local_vars') or {}).get('ck_legacy_c'):
            L += ['The sources were written before C99 (K&R declarations, functions used without a declaration):',
                  'GCC and clang compile them as GNU C89 (`-std=gnu89`), with what GCC 14 and clang 16 made errors',
                  'kept as warnings, as they were built when they were written; MSVC needs nothing.', '']
        if patches:
            L += ['## Changes to the CK sources', '',
                  'Only where they would not build or run on every target:', '']
            L += [f'- {p}' for p in patches]
            L.append('')
        L += ['## Licence', '',
              'The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers',
              'of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.', '']
        return '\n'.join(L)
