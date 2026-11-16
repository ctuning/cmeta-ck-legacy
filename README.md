# cMeta CK legacy experiments

The benchmarks and datasets of the Collective Knowledge framework (CK) and of the cTuning projects before it -
cBench, PolyBench, the cTuning MiDataSets, the codelets of the CK paper and MILEPOST GCC - originally created by
Grigori Fursin, **updated for cMeta and improved using cMeta's run-ai with Claude in 2026**: they build and run
again on today's compilers and devices, their outputs are checked against reference outputs, and the defects
this exposed in the original sources are fixed, each as a recorded patch.

More about cMeta: [cTuning.ai/project/cmeta](https://cTuning.ai/project/cmeta).

## Quick start

Install cMeta 0.43 or newer with its web server, cserver. The preferred way is the
[interactive installer](https://cTuning.ai/project/cmeta/cmeta.install/), which gives the commands for your OS,
shell and package manager. With [uv](https://github.com/astral-sh/uv) it is one line:

```sh
uv tool install --with pip --python ">=3.9,<3.15" "cmeta[server]"     # or: pip install "cmeta[server]"
```

Then:

```sh
cx repo pull ctuninglabs@cmeta-aops                        # its automations, 0.72 or newer
cx repo pull https://github.com/ctuning/cmeta-ck-legacy

cx program run cbench-consumer-jpeg-c cpu -q               # build and run on this machine
cx program run polybench-cuda-gemm cuda -q                 # on an NVIDIA GPU
cx program run polybench-opencl-gemm opencl -q             # on any OpenCL GPU
cx task run test-ck-programs --compute=cpu -q              # every program and command

cx app run cserver                                         # the web interface at http://127.0.0.1:8004
```

## What is here

| Programs | | Targets |
|---|---|---|
| cBench | 22, `program/cbench-*` | cpu, android-cpu |
| PolyBench/C 3.2 | 27, `program/polybench-cpu-*` | cpu, android-cpu |
| PolyBench/GPU 1.0 | 15 CUDA and 15 OpenCL, `program/polybench-cuda-*`, `program/polybench-opencl-*` | cuda, opencl, android-gpu |
| Codelets of the CK paper | 3, `program/shared-codelet-*` | cpu, android-cpu |

The datasets are one per kind of input, `dataset/ctuning-<kind>` with its inputs inside, and the office snapshots
of the CK paper. The tasks: `test-ck-programs` runs and compares the programs, `import-ck` converted them from CK,
`get-ctuning-dataset` fetches inputs on demand, and `extract-milepost-features-legacy` extracts the MILEPOST
features of a C program.

## The inputs

**The cTuning MiDataSets.** The smallest input of each kind is in this repository. The full set, 491 inputs in 23
kinds, is in two gated Hugging Face datasets of cTuning, under the same terms of use:

- [ctuning/cTuning-MiDataSets](https://huggingface.co/datasets/ctuning/cTuning-MiDataSets), a folder per kind,
  from where cMeta fetches a kind when a program needs it;
- [ctuning/cmeta-repo-ctuning-midatasets](https://huggingface.co/datasets/ctuning/cmeta-repo-ctuning-midatasets),
  the same inputs as a cMeta repository, to pull at once.

Request access on the page of the dataset you need; the maintainers review the requests. Then log in once on your
machine, and use them:

```sh
cx tool run hf -- auth login
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm/image-ppm-0007 -q   # fetches the kind
cx repo pull hf://ctuning/cmeta-repo-ctuning-midatasets                                   # or every input at once
```

> **A note on the MiDataSets.** They were collected from public web sources in 2006-2007 to evaluate compilers on
> realistic data, and the origin and licence of each file were not recorded, so their origin is unclear. The inputs
> in this repository and on the Hugging Face Hub are an archive for research purposes, to reproduce and extend the
> experiments of that time, and the licence of this repository does not cover them. If a file is yours and you
> want it removed, please open an issue.

**The office webcam snapshots of the CK paper**, the input of the codelets, by day and by night: on Zenodo,
[10.5281/zenodo.24275729](https://doi.org/10.5281/zenodo.24275729), from where cMeta fetches them, and on the
Hugging Face Hub, [ctuning/ck-office-snapshots](https://huggingface.co/datasets/ctuning/ck-office-snapshots).
CC-BY-4.0.

<p>
<img src="https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.day.data_orig.jpg" width="45%" alt="The office by day">
<img src="https://zenodo.org/records/24275729/files/dataset.ctuning-image-jpg-fgg-office.night.data_orig.jpg" width="45%" alt="The office by night">
</p>

## Reference outputs

The outputs of every program with its default values are in the Hugging Face dataset
[ctuning/cmeta-repo-ck-legacy-program-output](https://huggingface.co/datasets/ctuning/cmeta-repo-ck-legacy-program-output),
a cMeta repository:

```sh
cx repo pull hf://ctuning/cmeta-repo-ck-legacy-program-output
cx program run polybench-cpu-2mm cpu --check_output=validate -q      # a difference fails the run
cx program run polybench-cpu-2mm cpu --compile.n=512 --check_output -q   # records a new reference
```

They were recorded on Windows and hold on Linux, macOS and Android, and on NVIDIA, Intel, Apple and PowerVR GPUs.
Two runs differ, and are reported:

- `cbench-security-pgp --cmd=decode` on Windows prints 4 zero bytes before the text. CK's input was written by a
  64-bit Linux PGP 2.6, whose 4-byte timestamp field took 8 bytes, and the Windows build reads only 4.
- `polybench-opencl-fdtd-2d` on a PowerVR GPU differs from the CPU in one value beyond PolyBench's own threshold.

## The parameters of a run

| Option | What it changes |
|---|---|
| `--cmd=<command>` | the command of a program with several, such as `--cmd=decode` |
| `--dataset=<dataset>/<input>` | the input |
| `--repeat=<n>` | how many times the kernel runs |
| `--calibrate[=<seconds>]` | raises the repeat until a run lasts about that long, 4 s by default, as CK did |
| `--compile.size=mini\|small\|standard\|large\|extralarge` | PolyBench's array sizes |
| `--compile.n=<N>` | every PolyBench array dimension N |
| `--compile.precision=float\|double` | PolyBench's data type |
| `--compile.d.<NAME>=<value>` | any define of the build |

Each choice is part of the key of its reference output, and the summary printed after every run names them.

## MILEPOST GCC features

```sh
cx task run extract-milepost-features-legacy --source-file=example.c --output-file=features.json -q
```

The original GCC 4.4.4 and MILEPOST 2.1 tools extract the 55 static features of a C program in a container, from
the capsules of [10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695). See the
[task guide](task/extract-milepost-features-legacy/README.md).

## Licences

This repository's own content - the cMeta descriptions, tasks, notes and patches - is Apache-2.0 (`LICENSE`). The
program sources keep their authors' licences, listed program by program in [`LICENSES.md`](LICENSES.md). Two parts
state no licence: `filter.c` of the codelets, the UTDSP edge detection (copyright 1992 Mazen A.R. Saghir,
University of Toronto) as changed for the CK paper, and the MiDataSets inputs, whose origin is unclear. Both are
kept as an archive for research purposes.
