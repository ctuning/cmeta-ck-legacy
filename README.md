# cMeta CK legacy experiments

The older benchmarks and datasets of the Collective Knowledge framework (CK) and of the cTuning projects
before it - cBench, PolyBench, the cTuning MiDataSets, the codelets of the CK paper, MILEPOST GCC - originally
created by Grigori Fursin, **updated for cMeta and improved using cMeta's run-ai with Claude in 2026**: they
build and run again on today's compilers and devices (Windows, Linux, macOS and Android CPUs, NVIDIA GPUs with
CUDA 11 to 13, OpenCL GPUs), their outputs are compared across targets and their GPU results checked against
the CPU, and the defects this exposed in the original sources are fixed - each change recorded as a patch
with its reason (`task/import-ck/files/patches`, and `patches` in each program's `_desc.yaml`).

cMeta on cTuning.ai: [the cMeta project](https://cTuning.ai/project/cmeta) and its lists of
[targets](https://cTuning.ai/project/cmeta/cmeta.targets/), [programs](https://cTuning.ai/project/cmeta/cmeta.programs/),
[tools](https://cTuning.ai/project/cmeta/cmeta.tools/), [tasks](https://cTuning.ai/project/cmeta/cmeta.tasks/) and
[repositories](https://cTuning.ai/project/cmeta/cmeta.repos/).

Git operations use **ctuning-admin** and **admin@ctuning.org**. This repository is not required by the live
websites and is not synced to Azure; its tasks select no website ports.

## What is here

| Programs (82) | | Targets |
|---|---|---|
| cBench (22) | automotive-bitcount, automotive-qsort1, bzip2, consumer-jpeg-c, consumer-jpeg-d, consumer-lame, consumer-mad, consumer-tiff2bw, consumer-tiff2dither, consumer-tiff2median, consumer-tiff2rgba, network-dijkstra, network-patricia, office-stringsearch2, security-blowfish, security-pgp, security-rijndael, security-sha, telecom-adpcm-c, telecom-adpcm-d, telecom-crc32, telecom-gsm (`program/cbench-*`) | cpu, android-cpu |
| PolyBench/C 3.2 (27) | 2mm, 3mm, adi, atax, bicg, cholesky, doitgen, durbin, dynprog, fdtd-2d, fdtd-apml, gemver, gesummv, gramschmidt, jacobi-1d-imper, jacobi-2d-imper, lu, ludcmp, medley-floyd-warshall, medley-reg-detect, mvt, seidel-2d, symm, syr2k, syrk, trisolv, trmm (`program/polybench-cpu-*`) | cpu, android-cpu |
| PolyBench/GPU 1.0, CUDA (15) | 2dconv, 2mm, 3dconv, 3mm, atax, bicg, corr, covar, fdtd-2d, gemm, gesummv, gramschm, mvt, syr2k, syrk (`program/polybench-cuda-*`) | cuda |
| PolyBench/GPU 1.0, OpenCL (15) | the same kernels (`program/polybench-opencl-*`) | opencl, android-gpu |
| Codelets of the CK paper (3) | filter, filter5, adaptive-filter: edge detection of a 1536 x 1536 image, the adaptive one tuned for the day and the night snapshot (`program/shared-codelet-*`) | cpu, android-cpu |

| Datasets (28, with 501 inputs) | |
|---|---|
| cBench inputs, the cTuning MiDataSets (23 datasets, 491 inputs) | one dataset per kind of input, its inputs as sub-datasets: adpcm (20), au (20), audio-mp3 (20), audio-wav (20), benc (20), bzip2 (32), cdataset-dijkstra (20), cdataset-patricia (20), cdataset-qsort (20), enc (20), gsm (20), image-jpeg (20), image-pgm (21), image-pgm-clean-gray-square (8), image-ppm (20), image-tiff (30), image-tiff-bw (30), image-tiff-nocomp (30), number (20), pcm (20), pgp (20), ps (20), txt (20) (`dataset/ctuning-<kind>`). The small input of each kind, the one cBench takes by default, is in the repository (`files/<input>/`); the others are fetched on demand, a kind at a time, from the Hugging Face dataset [ctuning/cTuning-MiDataSets](https://huggingface.co/datasets/ctuning/cTuning-MiDataSets) (access on request) |
| Office webcam snapshots of the CK paper (5 datasets, 10 inputs) | the day and the night snapshot as sub-datasets, as JPEG, PPM, binary pixels (the codelets' input) and text, full size and small (`dataset/ctuning-image-*-fgg-office*`); their files are fetched on demand from their Zenodo record [10.5281/zenodo.24275729](https://doi.org/10.5281/zenodo.24275729) (also on the Hub: [ctuning/ck-office-snapshots](https://huggingface.co/datasets/ctuning/ck-office-snapshots)) |

| Tasks (4) | |
|---|---|
| `extract-milepost-features-legacy` | the 55 static features of a C program by the original MILEPOST GCC (in a container) |
| `import-ck` | the conversion of CK programs and datasets, and `LICENSES.md` |
| `test-ck-programs` | every program and command on a target, on every input, the outputs compared, the checks |
| `get-ctuning-dataset` | the sets of inputs on demand from their records: the office snapshots' files from Zenodo, the MiDataSets capsules from a folder (the MiDataSets datasets fetch from the Hub with cmeta-aops's `get-hf-dataset`) |

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
CUDA (15) and OpenCL (15) into `program/`, and the sets of their inputs into `dataset/`. They inherit
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

### The inputs

> **A note on the MiDataSets inputs.** The cTuning MiDataSets were collected from public web sources in
> 2006-2007 to evaluate compilers on realistic data, and the origin and licence of each file were not recorded,
> so their origin is unclear. The small inputs kept in this repository and the full set on the Hugging Face Hub
> are an archive for research purposes - to reproduce and extend the experiments of that time - and the
> licence of this repository does not cover them. If a file is yours and you want it removed, please open an
> issue.

Every kind of input of cBench is one dataset, `dataset/ctuning-<kind>`, and its inputs are its sub-datasets:
`sub_datasets` of the dataset's `_desc.yaml` lists them in order - the first is what a program takes by
default - each with its files in the order a program takes them, its size, its tags, the number it stands for
and its CK entry. The small input of each kind (CK's `ctuning-datasets-min`) is in the repository,
`files/<input>/`; the full cTuning MiDataSets (491 inputs, about 20 per kind) are fetched on demand from
the Hugging Face dataset [ctuning/cTuning-MiDataSets](https://huggingface.co/datasets/ctuning/cTuning-MiDataSets)
- a kind at a time, downloaded once into the cMeta file cache by `get-hf-dataset` (cmeta-aops). The
dataset is gated: ask for access on its page once (the inputs were collected from public web sources in
2006-2007 and their origins were not recorded, so they are shared for research under its terms of use), then
log in once on the machine (`cx tool run hf -- auth login`). A program selects its dataset by tags;
`--dataset=<dataset>/<input>` names an input, and a set grows by a folder and a line:

```sh
cx program run cbench-consumer-jpeg-c cpu -q                                          # ctuning-image-ppm/image-ppm-0001
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm/image-ppm-0007 -q
cx task run test-ck-programs --programs=cbench-* --all_datasets -q                    # every input of every program
```

The codelets of the CK paper repository - an edge-detection filter on a 1536 x 1536 image and its
adaptive version, tuned for a day and a night snapshot (`--time=day|night`) - are the programs
`shared-codelet-*`, and the two office webcam snapshots they used are the datasets
`dataset/ctuning-image-*-fgg-office*` with `day` and `night` as sub-datasets - as JPEG, PPM, the binary
pixels the codelets read, and text. Their files are published one by one in the Zenodo record of the
snapshots, [10.5281/zenodo.24275729](https://doi.org/10.5281/zenodo.24275729) (CC-BY-4.0;
`dataset.<dataset>.<input>.<file>`, from where `get-ctuning-dataset` fetches them) - the
[day](https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.day.data_orig.jpg) and the
[night](https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.night.data_orig.jpg) snapshot:

<p>
<img src="https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.day.data_orig.jpg" width="45%" alt="The office by day">
<img src="https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.night.data_orig.jpg" width="45%" alt="The office by night">
</p>

```sh
cx program run shared-codelet-adaptive-filter cpu --time=night --dataset=ctuning-image-raw-bin-fgg-office/night -q
```

`task/test-ck-programs` runs every program and command on a target (`--all_datasets`: on every input)
and compares the outputs of several targets.

### Reference outputs

What each program must produce for a given command, input and parameters is kept as `program.output`
artifacts (cmeta-aops) in the repository
[ctuning/cmeta-repo-ck-legacy-program-output](https://huggingface.co/datasets/ctuning/cmeta-repo-ck-legacy-program-output)
on the Hugging Face Hub - a cMeta repository pulled with `cx repo pull hf://ctuning/cmeta-repo-ck-legacy-program-output`.
With it plugged, `--check_output` compares a run with its reference (a difference fails the run), or records
one when none exists yet; `--output_repo` names where a recording goes:

```sh
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm/image-ppm-0007 --check_output -q
cx task run test-ck-programs --programs=cbench-* --all_datasets --extra="--check_output --output_repo=cmeta-repo-ck-legacy-program-output" -q
```

What is compared is what CK compared (`run_correctness_output_files` of its metas: the files a program writes
and the standard error of every program, `tmp-output2.tmp`), and the standard output where the result is
(dijkstra, patricia, sha); the outputs that hold something of the machine or of the moment (the path of the
input in a TIFF, a signature's time, LAME's progress) are not: `output_check:` of each program's `_desc.yaml`
(`files`, `skip`; `task/import-ck/_desc.yaml` keeps the additions). PolyBench/C compares the arrays it dumps,
within a relative tolerance and one step of the 2 decimals it prints (x86 and arm64 round differently);
PolyBench/GPU compares its standard output without the lines that name the device (`ignore_lines`), so its
reference says that the GPU's result matched the CPU's - on any GPU. A case is keyed by the command, the input
and the parameters of the run - for every program the kernel's `repeat`, for PolyBench the defines of the build
(the sizes, `DATA_TYPE`, the dump), for the adaptive codelet its `--time` - and records the host, the targets,
the tools, the parameters and the times it was made with (`case.json`).

The references of every program with its default values - cBench on all its commands, PolyBench/C, the codelets,
PolyBench/GPU on CUDA and on OpenCL - were recorded on Windows 11 (MSVC 19.51, an NVIDIA RTX GPU) and validate on
Ubuntu 26.04 and 24.04, Debian 12 and Fedora 44 (GCC) and macOS (Apple clang, arm64), and the OpenCL ones on Intel,
Apple and older NVIDIA GPUs too. One run differs by design: `cbench-security-pgp --cmd=decode`. PGP 2.6 writes and
reads the timestamp of its literal packet as a `word32`, an `unsigned long` - 8 bytes on 64-bit Linux and macOS, 4
on Windows - and CK's input `data.pgp` was written by a 64-bit Linux build, with an 8-byte timestamp. Linux and
macOS read it back as written; Windows reads 4 bytes, and the other 4 (zeros) come out in front of the text. The
reference holds the plaintext, and the Windows run is reported.

### The parameters of a run

Every program repeats its kernel `--repeat=<n>` times (CK's `CT_REPEAT_MAIN`), and `--calibrate[=<seconds>]`
raises the repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds),
as CK's calibration did. PolyBench programs are built with CK's sizes, or `--compile.size=mini|small|standard|
large|extralarge` (the header's), or `--compile.n=<N>` (every dimension N: square arrays); `--compile.precision=
float|double` sets `DATA_TYPE`, `--compile.d.<NAME>=<value>` any define, `--compile.dump=yes|no` the dump of the
arrays. Each choice is a build of its own, and the summary printed after every run names the parameters and the
defines the run was made with:

```sh
cx program run cbench-automotive-susan cpu --cmd=edges --repeat=20 -q
cx program run cbench-security-sha cpu --calibrate=10 -q
cx program run polybench-cpu-2mm cpu --compile.n=512 --compile.precision=float --repeat=3 -q
cx program run polybench-cuda-gemm cuda --compile.n=1024 --check_output -q
```

## Licences

This repository's own content - the cMeta descriptions, tasks, notes and patches - is Apache-2.0
(`LICENSE`). The sources of the converted programs keep the licences of their authors (GPL, LGPL, BSD,
IJG, libtiff, PolyBench/C 3.2 under the GPLv2 ...), each in the program's `src/`: **`LICENSES.md`**
lists the licence of every program and dataset, generated from their descriptions
(`cx task run import-ck --licenses_md`).

Two parts state no licence. The edge-detection filter of the codelets, `filter.c`, comes from the UTDSP
benchmark suite (copyright 1992 Mazen A.R. Saghir, University of Toronto) and was changed for the CK paper; it is
kept as that paper's repository published it. The MiDataSets inputs have an unclear origin (see the note in "The
inputs"). Both are kept as an archive for research purposes.

## Git identity

Commits are made with the ctuning-admin account's SSH authentication/signing key.
Transport, author email and signing key are pinned in this repository's local Git
settings. Credentials and `.git` settings are not repository content.
