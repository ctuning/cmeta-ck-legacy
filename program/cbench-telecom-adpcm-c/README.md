# cbench-telecom-adpcm-c

cBench (MiBench-based, cTuning): the CK program `cbench-telecom-adpcm-c` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-telecom-adpcm-c cpu -q
cx program run cbench-telecom-adpcm-c --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `encode` | `pcm,audio` | `(the first)` | `{qinput_files.data} tmp-output.tmp` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`); `--calibrate[=<seconds>]` raises the
repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds).
Standard output and error go to `tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on
iOS); the times of the kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).
The summary printed after the run names the parameters and the defines of the build; `--check_output`
compares the outputs with the reference of the same command, input and parameters (`program.output`),
or records one.

## Changes to the CK sources

Only where they would not build or run on every target:

- rawcaudio.c: reads and writes the files given on its command line (else the standard streams, as before), in binary mode, with fread/fwrite instead of read(0)/write(1) (no <unistd.h>; an iOS app has no redirection, Windows reads the standard streams in text mode)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
