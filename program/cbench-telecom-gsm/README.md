# cbench-telecom-gsm

cBench (MiBench-based, cTuning): the CK program `cbench-telecom-gsm` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-telecom-gsm cpu -q
cx program run cbench-telecom-gsm --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `default` | `audio,au` | `(the first)` | `-fps -c {qinput_files.data}` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`); `--calibrate[=<seconds>]` raises the
repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds).
Standard output and error go to `tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on
iOS); the times of the kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).
The summary printed after the run names the parameters and the defines of the build; `--check_output`
compares the outputs with the reference of the same command, input and parameters (`program.output`),
or records one.

The sources were written before C99 (K&R declarations, functions used without a declaration):
GCC and clang compile them as GNU C89 (`-std=gnu89`), with what GCC 14 and clang 16 made errors
kept as warnings, as they were built when they were written; MSVC needs nothing.

## Changes to the CK sources

Only where they would not build or run on every target:

- config.h: without unistd.h and utime on Windows (WINDOWS), which has neither (toast.c already leaves fchmod and fchown out there)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
