# Independent MILEPOST feature extraction

Author: Grigori Fursin.

Extracts the original 55 MILEPOST static program features (ft1-ft55) of a C89 program with the
recovered MILEPOST GCC 4.4.4 / ICI 2.05 / MILEPOST 2.1 / XSB 3.2 / CCC tools of 2010, without any
website, port or server:

```sh
cx task run extract-milepost-features-legacy,4e719bc8239d4ece --source-file=example.c --output-file=features.json -q
```

The result holds the feature string, the 55 values, the historical versions and timings.


## The capsules

The runtime is made from five public capsules (`20261114.*.linux-amd64.tar.gz`: MILEPOST GCC, XSB,
CCC, the compiler support tools, the C headers), published with all their sources and licences in the
archive record [10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695); the task downloads
them from there by default. `--capsules` names another place:

- a folder holding the five files, or
- a URL: a template with `{name}` (e.g. `https://zenodo.org/records/<id>/files/{name}?download=1`)
  or a base URL the file names are appended to.

Every file is checked against its SHA-256 in `src/milepost.py` before anything is installed.
`--capsules` can also come from `CMETA_MILEPOST_CAPSULES`; the default is `default_capsules` in
`_desc.yaml` (`https://zenodo.org/records/24246695/files/{name}?download=1`).


## How it runs

The first of these that applies:

1. `--endpoint=<URL>` - a private HTTP extraction service;
2. `--worker=<cMeta host>` - the service on a cMeta host;
3. `--runtime-root=<folder>` (or `CMETA_MILEPOST_ROOT`) - natively, Linux amd64 only;
4. otherwise (the default, on any machine): a Linux container.

Container mode (`--engine=docker|podman`, `--image`, `--volume`; defaults in `_desc.yaml`):
the runtime is prepared once into the engine volume `cmeta-milepost-legacy-20261114` (about 400 MB,
a few seconds from a local folder) by a container of `python:3.12-slim`; every extraction then runs in
a new container with that volume read-only, no network, no capabilities and an unprivileged user. The
C source goes in on stdin and the result comes back on stdout, so no path has to exist inside the
container. On Windows and macOS this needs Docker Desktop (or Podman); on ARM machines the amd64 image
runs under emulation. Remove the runtime with `docker volume rm cmeta-milepost-legacy-20261114`.

Native mode: `--runtime-root` names a writable folder; with `--capsules` the runtime is prepared there
when it is not ready yet. It needs Linux amd64 with glibc 2.38 or newer (Ubuntu 24.04+, Debian 13+,
Fedora 39+, RHEL/Rocky 10): the compiler of 2010 runs on older systems, but the assembler, make and
uuidgen of the support capsule come from Ubuntu 24.04. Elsewhere use the container mode.

Leave out `--source-file` to only prepare the runtime.

By hand, natively:

```sh
python3 src/milepost.py prepare --root=/path/legacy-runtime --capsules=/path/capsules
echo '{"source": "int f(int x){return x+1;}"}' | python3 src/milepost.py extract --root=/path/legacy-runtime
```

`extract --work=<folder>` keeps the jobs and the lock outside the runtime, which can then be read-only.
The private capture of 2026-10-20 (`--capture=<.../20261020-153341.recovered-runtime>`, sibling
`20261020-headers`) is still accepted, and runtimes prepared from it stay valid; a runtime keeps the
capsule set it was made from.


## Limits

GNU89/C89 source of at most 64 KiB. The program is only compiled for analysis, never executed;
compilation has time, memory, process and file limits; temporary files are removed. The historical
driver may exit with 1 even when it wrote all 55 features: the result is judged by the features.


## Tested

2026-11-14 (test session `20261114/1839.milepost-capsules`): the task through cx on Windows in container
mode (Docker Desktop) - preparing from a folder and from a URL in the archive's form, the 55 values of
the 2026-10-20 baseline, a stdio program, invalid C, reuse; the capsules directly in containers of
Debian 13 (Python 3.9, 3.12, 3.15), Ubuntu 26.04 and Fedora 44; a corrupted download refused; the
runtime from the public capsules identical to the private capture's except the cleaned password lines.
Debian 12 and Rocky 9 fail natively (glibc too old for the support tools), as described above.

This experimental task has a different UID from the unchanged live website task.
