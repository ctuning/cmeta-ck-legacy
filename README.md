# cMeta CK legacy experiments

Independent archival experiments with the historical MILEPOST GCC and ctuning-cc
pipeline, originally created by Grigori Fursin. Git operations use **ctuning-admin**
and **admin@ctuning.org**.

This repository is not required by the live websites and is not synced to Azure.
It has a separate experimental task UID and selects no website ports by default.

## Extract features from a C program

On any machine with Docker or Podman (Windows, macOS, Linux), with cMeta and its
usual AOps task category installed:

```sh
cx task run extract-milepost-features-legacy,4e719bc8239d4ece --source-file=example.c --output-file=features.json -q
```

The task prepares the original GCC 4.4.4 / ICI 2.05 / MILEPOST 2.1 / XSB 3.2 / CCC
tools once into a container volume and extracts the original 55 static features in a
throwaway Linux container (read-only runtime, no network). It uses no website, port or
credentials. Use GNU89/C89 programs of at most 64 KiB; the program is not executed.
On Linux amd64 with glibc 2.38+, `--runtime-root=<folder>` runs the tools natively.
See the [task guide](task/extract-milepost-features-legacy/README.md).

The binary capsules are deliberately separate from Git source: five public files
`20261114.*.linux-amd64.tar.gz`, published with all their sources and licences in
the archive record [10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695),
from which the task downloads them by default (`--capsules` names another folder or
URL). The task source contains their SHA-256 checksums. The older private captures are
still accepted (`--capture`); they are not published.

## cBench, PolyBench/C and PolyBench/GPU programs, their inputs

`task/import-ck` converted the CK programs cBench (22), PolyBench/C 3.2 CPU (27) and PolyBench/GPU 1.0
CUDA (15) and OpenCL (15) and their small inputs into `program/` and `dataset/`. They inherit
`template-c-cpu` and the hooks of `template-ck-program` (cmeta-aops, so they need a cmeta-aops with that
template), use its run-time libraries (`lib-xopenme`, `lib-polybench`, `lib-cuda`, `lib-opencl`) and run
on the host CPU of Windows (MSVC, clang), Linux (GCC, clang) and macOS (clang), on Android
(`--compute=android-cpu`) and, the PolyBench/GPU ones, on an NVIDIA GPU (`--compute=cuda`) or any OpenCL
device (`--compute=opencl`; `--compute=android-gpu` on an Android device):

```sh
cx program run cbench-consumer-jpeg-c cpu -q
cx program run cbench-bzip2 cpu --cmd=decode -q
cx program run polybench-cpu-2mm cpu --compile.size=large -q
cx program run polybench-cuda-gemm cuda -q
cx program run polybench-opencl-gemm opencl -q
```

The CUDA programs build with CUDA 11, 12 and 13 (`--use.nvcc.version=11.8`; the toolkit is taken from the
system or installed into the cMeta cache, with a host compiler it accepts - on Linux with glibc 2.41 and
newer only CUDA 13, which cMeta says); the OpenCL ones run on the first GPU the `opencl` target finds, or
`--opencl_device=<number or a word of its name>` (`--opencl_device=intel`), and on the GPU of an Android
device (`--compute=android-gpu`). Both check their result against the CPU's (the reference CK left in a
comment; `--compile.check=no` builds them as CK did).

The full cTuning MiDataSets (491 inputs, about 20 per program) are datasets too
(`dataset/ctuning-<kind>-<nnnn>`); `task/get-ctuning-dataset` fetches their files on demand from the
capsules (one download per kind, checked and cached):

```sh
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm-0007 -q
```

The codelets of the CK paper repository - an edge-detection filter on a 1536 x 1536 image and its
adaptive version, tuned for a day and a night snapshot (`--time=day|night`) - are the programs
`shared-codelet-*`, and the two office webcam snapshots they used are datasets fetched on demand from
their own capsule (`dataset/ctuning-*fgg-office*`):

```sh
cx program run shared-codelet-adaptive-filter cpu --time=night --dataset=ctuning-image-raw-bin-fgg-office-night-gray -q
```

`task/test-ck-programs` runs every program and command on a target (`--all_datasets`: on every input)
and compares the outputs of several targets.

## Licences

This repository's own content - the cMeta descriptions, tasks, notes and patches - is Apache-2.0
(`LICENSE`). The sources of the converted programs keep the licences of their authors (GPL, LGPL, BSD,
IJG, libtiff, PolyBench/C 3.2 under the GPLv2 ...), each in the program's `src/`: **`LICENSES.md`**
lists the licence of every program and dataset, generated from their descriptions
(`cx task run import-ck --licenses_md`).

## Git identity

Commits are made with the ctuning-admin account's SSH authentication/signing key.
Transport, author email and signing key are pinned in this repository's local Git
settings. Credentials and `.git` settings are not repository content.
