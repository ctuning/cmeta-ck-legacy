# MILEPOST GCC through cMeta: archived capsules on Zenodo and tests (2026-11-14/15)

Author: Grigori Fursin.

**Zenodo:** [https://doi.org/10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695)
(record https://zenodo.org/records/24246695; all versions: 10.5281/zenodo.24246694)

The machine-learning-enabled compiler MILEPOST GCC of 2010 (MILEPOST 2.1 on GCC 4.4.4 with ICI 2.05,
the XSB 3.2 Prolog feature extractor and the CCC framework of cTuning CC 2.5) runs again, fully
automatically, on any machine with Docker or Podman - through the cMeta task
`task::extract-milepost-features-legacy,4e719bc8239d4ece` of this repository, which downloads the
archived binaries from Zenodo and extracts the original 55 MILEPOST static program features (ft1-ft55)
of a C program.

This note records what was archived, how to use it and what was tested. Its files: `_run.bat` and
`_run.sh` (run the task on the examples or on your programs), `compare.py` (the reference check),
`examples/` and `reference/` (C programs and their 55 values).

It works on Windows (Docker Desktop), Linux (Docker or Podman, or natively with glibc 2.38+) and
macOS (Docker Desktop; on Apple Silicon the x86-64 container is emulated) - all three tested.


## The archive record

[10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695) (https://zenodo.org/records/24246695,
published 2026-11-15, open access; concept DOI 10.5281/zenodo.24246694). Ten files, about 256 MB:

| File | Bytes | SHA-256 |
|---|---:|---|
| 20261114.milepost-gcc-4.4.4.linux-amd64.tar.gz | 111046726 | a211129cf85f8c9df196185880955d59504e672d89becb8f5daff09db7575c84 |
| 20261114.xsb-3.2.linux-amd64.tar.gz | 6695173 | 290fdc244b95596b617a3c0a2ba54c5127350995d7688fb1aa8d97eadb760778 |
| 20261114.ccc-framework.linux-amd64.tar.gz | 754822 | 65a6e1fd41ba7d8a4d4ebb6eda7db1016a070a5a68bee76b3145c0e00dc8d0ff |
| 20261114.compiler-support.linux-amd64.tar.gz | 1461431 | 3bf0c3f8ba735d446e1b068bc19334cc786abdf17262ff5ceb45add34bc8e04f |
| 20261114.compiler-headers.linux-amd64.tar.gz | 2286886 | 587ffad6386f86d4cd0ce76cbd241f9c92e59eca17e7e8462e40642d32eb9f87 |
| 20261114.sources.ctuning-cc-2.5-gcc-4.4.4-ici-2.05-milepost-2.1.tar.gz | 92364942 | 7f2c757d283e659d6323f2132f4b28051e76ef56d9be8c76bdb6b46c22a8801a |
| 20261114.sources.compiler-support.ubuntu-24.04.tar | 41359360 | db0d0165a6d2eb408adb585b5da19060611c48f23314113bb22b432a6348c478 |
| 20261114.licenses.tar.gz | 125021 | d66d660863887e7a380b87119920563f009bee4374f6e152703051fbade0be45 |
| 20261114.README.md | 11283 | 0e77bb484282bb69881ff9aadc66c3a3fbf2be8d06ef2a5ef55abda6d9a7e906 |
| 20261114.SHA256SUMS | 975 | (the SHA-256 of the other nine) |

- The five binary capsules (Linux x86-64) extract into one folder: `milepost/` (GCC 4.4.4 with the
  ICI 2.05 plugins, `ml-feat-proc`, `ctuning-cc`, GMP, MPFR, MPC, PPL, CLooG/isl), `milepost/3.2`
  (XSB), `ccc-framework/`, `support/` (GNU as, make, uuidgen and their libraries from Ubuntu 24.04)
  and `headers/usr/include` (C library and Linux headers from Ubuntu 24.04).
- Every corresponding source is inside the record: the cTuning CC 2.5 source release of 2010 (from
  SourceForge, original SHA-256 `eb0cf937bd56a6d49985a273570def56c9d0295f8f8b6049862e0c96feec8ab3`)
  and the five Ubuntu source packages of the support binaries, plus every licence text.
- Provenance: the binaries were captured on 2026-10-20 from the original 2010 installation; the
  support files are byte-identical to Ubuntu noble's binutils 2.42-4ubuntu2.8, make-dfsg
  4.3-4.1build2, util-linux 2.39.3-9ubuntu6.4, zlib 1:1.3.dfsg-3.1ubuntu2.1, libzstd
  1.5.5+dfsg2-2build1.1; the headers to libc6-dev 2.39-0ubuntu8.6 and linux-libc-dev 6.8.0-90.91.
- The only change to the historical files: the values of old, long-retired database and
  web-service passwords in 16 CCC configuration scripts (and 3 files of the 2010 source release)
  were removed; `licenses/REDACTIONS.md` in the record lists every changed line.
- Licences: free and open source - GPL-3.0-or-later (GCC 4.4.4 with the runtime library exception,
  PPL, binutils, make), GPL-2.0-only (ICI plugins, MILEPOST feature extractor, cTuning CC wrapper,
  CCC), LGPL-2.1-or-later / LGPL-3.0-or-later (MPFR, MPC, CLooG, isl, GMP, C library headers),
  LGPL-2.0 (XSB), GPL-2.0 WITH Linux-syscall-note (Linux headers), BSD-3-Clause, Zlib.


## Using it

With cMeta and cmeta-aops installed, this repository plugged and Docker (or Podman) running - on
Windows (cmd):

```bat
cx task run extract-milepost-features-legacy --source-file=vector-stats.c --output-file=vector-stats.features.json -q
```

on Linux or macOS the same words. [examples/vector-stats.c](examples/vector-stats.c) gives

```
ft1=10, ft2=4, ft3=3, ft4=0, ft5=5, ft6=3, ft7=0, ft8=3, ft9=1, ft10=1, ft11=2, ft12=0, ft13=8, ...
```

and [examples/vector-stats.features.json](examples/vector-stats.features.json) (`ok`, `feature_count`,
the GCC / ICI / MILEPOST versions, `features`, `values` ft1..ft55, `wall_seconds`).

The scripts of this note do it for the examples or for your programs and check the reference program
against the values of 2026-10-20:

```bat
rem Windows (cmd), Docker Desktop running: both examples + the reference check
_run.bat

rem your programs
_run.bat my.c other.c

rem options go to the task ("--name=value" may also be quoted)
_run.bat my.c --engine=podman
```

```sh
# Linux and macOS (Docker Desktop / Docker / Podman running)
bash _run.sh
bash _run.sh my.c other.c
bash _run.sh --runtime-root=$HOME/milepost-runtime my.c    # Linux amd64 with glibc 2.38+: natively, no container
```

The results go to `results/` beside the scripts (`MILEPOST_RESULTS=<folder>` for another one); the
exit status is 1 when a program fails or the reference check differs.

What happens: the first run on a machine downloads the five binary capsules from the record
(`https://zenodo.org/records/24246695/files/{name}?download=1`, the task's `default_capsules`),
checks each SHA-256 and prepares them in the engine volume `cmeta-milepost-legacy-20261114` (about
400 MB) in a `python:3.12-slim` container; every extraction then runs in a new container with that
volume read-only, no network, no capabilities and an unprivileged user; the C source goes in on stdin
and the result comes back on stdout.

Options: `--capsules=<folder or URL>` (another copy of the capsules), `--engine=podman`, `--image`,
`--volume`; without `--source-file` the runtime is only prepared; `--runtime-root=<folder>` runs the
tools natively on Linux amd64 with glibc 2.38 or newer. The task guide:
[task/extract-milepost-features-legacy/README.md](../../task/extract-milepost-features-legacy/README.md).
Without cMeta, the record's `20261114.README.md` has a shell recipe for Linux.

Programs: C89 / GNU89, at most 64 KiB; standard headers are fine; the program is only compiled, never
run. Invalid C fails with "Could not extract features. Check that the program is valid C89 (GNU89)."
and the compiler diagnostics in the output file. A program with several functions gives ONE vector:
the sum of the per-function vectors (the CCC tool `ccc-ml-accumulate-features`; checked with two
functions, all 55 values, in either order).


## What was tested

The reference: [reference/example.c](reference/example.c) and its 55 values
[reference/example.features.json](reference/example.features.json), extracted on 2026-10-20 with the
original installation. Every check below compares all 55 values with them.

| Date | Where | What | Result |
|---|---|---|---|
| 2026-11-14 | Containers on a Windows laptop (Docker Desktop 29.9.3), no network | prepare from a folder (4.5 s) and from a URL (3.2 s), the reference program, a `stdio.h` program, a two-function program, invalid C, reuse (0.09 s), a corrupted download (refused, nothing installed), the old private capture (still accepted) | 21/21; the installed runtime is file-for-file identical to the one from the original capture except the 16 cleaned scripts |
| 2026-11-14 | Containers: Debian 13 with Python 3.9, 3.12, 3.15; Ubuntu 26.04; Fedora 44 | prepare and extract directly | all pass |
| 2026-11-14 | Containers: Debian 12 (glibc 2.36), Rocky Linux 9 (glibc 2.34) | the same | fail: the Ubuntu 24.04 support tools need GLIBC_2.38 (the 2010 compiler itself runs) |
| 2026-11-14 | The record's shell recipe, as written, in `python:3.12-slim` | without cMeta | 55 values equal |
| 2026-11-14 | The task through `cx` on the Windows laptop, container mode | folder and a URL in Zenodo's form; ~6 s first prepare, ~2 s per extraction | 8/8 |
| 2026-11-15 | The published record, from the laptop | all ten files: size + MD5 as published; downloaded through the task's URL form, SHA-256 | all equal |
| 2026-11-15 | A second machine (a Linux laptop, Ubuntu 26.04.1, glibc 2.43, Docker 29.1.3), nothing prepared | the plain command, defaults only: Docker 10.8 s first (Zenodo download included), 1.8 s after; natively 8.4 s first, 0.33 s after; a `stdio.h` program, invalid C | 8/8; the `stdio.h` values equal to the laptop's |
| 2026-11-15 | The Windows laptop, the plain command from Zenodo | examples/vector-stats.c: 21 s first, 1.9 s after; the multi-function check | as above |
| 2026-11-15 | The Windows laptop, `_run.bat` through cmd.exe | no arguments, an own program, options before and after it, a quoted option, invalid C, the default results folder | 6/6 (cmd splitting `--name=value` at the `=` found and handled) |
| 2026-11-15 | Ubuntu 26.04.1 (the second machine), `bash _run.sh` | defaults from an empty volume; an own program and the reference natively (`--runtime-root`); invalid C | all pass, reference check equal |
| 2026-11-15 | macOS 27.2 on Apple Silicon (Docker Desktop 29.9.2, x86-64 emulated), `bash _run.sh` in a throwaway cMeta home with a fresh cmeta-aops | defaults from Zenodo: 31 s first, 2 s after; an own program; invalid C; `--runtime-root` refused ("requires Linux amd64") | all pass; the values equal to the Windows laptop's |

Records: the cMeta test sessions 20261114/1839.milepost-capsules, 20261115/1411.milepost-zenodo,
20261115/1420.milepost-example and 20261115/1618.milepost-run-scripts of the author.


## Limits

- Linux x86-64 binaries: on Windows, macOS, ARM (emulated) or Linux with glibc older than 2.38 the
  task uses a container; only the container mode needs Docker or Podman.
- One feature vector per program (summed over its functions); per-function vectors would need the
  ICI plugin's own output.
- The historical driver may exit with 1 even when it wrote all 55 features: the task judges the
  result by the features.


## References

- G. Fursin et al. Milepost GCC: Machine Learning Enabled Self-tuning Compiler. International Journal
  of Parallel Programming 39(3):296-327, 2011. https://doi.org/10.1007/s10766-010-0161-2
- The 2010 source release: https://sourceforge.net/projects/c-tuning/files/cTuning-CC/V2.5-pre-release/
- Earlier MILEPOST records on Zenodo: 10.5281/zenodo.4005600 (project experience, 2020),
  10.5281/zenodo.2460873 (reproduce-milepost-project, 2018).
- The task commit: fc7b2e6 (2026-11-15).
