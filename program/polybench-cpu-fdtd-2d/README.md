# polybench-cpu-fdtd-2d

PolyBench/C 3.2 (Ohio State University), CK version: the CK program `polybench-cpu-fdtd-2d` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`).

## Run

```bash
cx program run polybench-cpu-fdtd-2d cpu -q
cx program run polybench-cpu-fdtd-2d --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

Sizes: CK's by default (NX=16, NY=16, TMAX=2), with the arrays dumped into `tmp-ck-output-dump.txt`
(the result to compare between targets). `--compile.size=mini|small|standard|large|extralarge`
takes the sizes of PolyBench's header instead, without the dump unless `--compile.dump=yes`;
`--compile.dump=no` leaves the dump out. Each choice is a build of its own.

```bash
cx program run polybench-cpu-fdtd-2d cpu --compile.size=large -q
```

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- fdtd-2d.h: the printf format of DATA_TYPE by token pasting (MSVC refuses "#if DATA_TYPE == double")
- fdtd-2d.c: print_array writes the arrays into tmp-ck-output-dump.txt (not the standard streams)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
