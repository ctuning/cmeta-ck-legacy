# polybench-cpu-fdtd-apml

PolyBench/C 3.2 (Ohio State University), CK version: the CK program `polybench-cpu-fdtd-apml` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`).

## Run

```bash
cx program run polybench-cpu-fdtd-apml cpu -q
cx program run polybench-cpu-fdtd-apml --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

Sizes: CK's by default (CXM=16, CYM=16, CZ=16), with the arrays dumped into `tmp-ck-output-dump.txt`,
(the result to compare between targets). `--compile.size=mini|small|standard|large|extralarge`
takes the sizes of PolyBench's header instead, without the dump unless `--compile.dump=yes`;
`--compile.n=<N>` makes every dimension N (square arrays); `--compile.dump=no` leaves the dump out;
`--compile.precision=float|double` sets `DATA_TYPE`; `--compile.d.<NAME>=<value>` any define. Each
choice is a build of its own, and part of the key of its reference outputs.

```bash
cx program run polybench-cpu-fdtd-apml cpu --compile.size=large -q
cx program run polybench-cpu-fdtd-apml cpu --compile.n=512 --compile.precision=float -q
```

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`); `--calibrate[=<seconds>]` raises the
repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds).
Standard output and error go to `tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on
iOS); the times of the kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).
The summary printed after the run names the parameters and the defines of the build; `--check_output`
compares the outputs with the reference of the same command, input and parameters (`program.output`),
or records one.

## Changes to the CK sources

Only where they would not build or run on every target:

- fdtd-apml.h: the printf format of DATA_TYPE by token pasting (MSVC refuses "#if DATA_TYPE == double")
- fdtd-apml.c: print_array writes the arrays into tmp-ck-output-dump.txt (not the standard streams)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
