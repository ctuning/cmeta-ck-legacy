# cbench-security-sha

cBench (MiBench-based, cTuning): the CK program `cbench-security-sha` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-security-sha cpu -q
cx program run cbench-security-sha --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `default` | `doc,txt` | `data.txt` | `{qinput_files.data}` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`); `--calibrate[=<seconds>]` raises the
repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds).
Standard output and error go to `tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on
iOS); the times of the kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).
The summary printed after the run names the parameters and the defines of the build; `--check_output`
compares the outputs with the reference of the same command, input and parameters (`program.output`),
or records one.

## Changes to the CK sources

Only where they would not build or run on every target:

- sha.h: the 32-bit words of the digest as unsigned int (unsigned long is 64 bits on Linux, macOS and Android, where the digest was wrong and changed with the compiler), and LITTLE_ENDIAN where the system headers do not define it (Windows): every target is little-endian; the digest is now the SHA-0 of the file on every target (SHA-1 with -DUSE_MODIFIED_SHA)
- sha.c: the digest printed as unsigned long, as its format says

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
