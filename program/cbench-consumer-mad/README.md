# cbench-consumer-mad

cBench (MiBench-based, cTuning): the CK program `cbench-consumer-mad` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-consumer-mad cpu -q
cx program run cbench-consumer-mad --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `default` | `audio,mp3` | `(the first)` | `--time=10000 --output=wave:tmp-output.tmp {qinput_files.data}` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

The sources were written before C99 (K&R declarations, functions used without a declaration):
GCC and clang compile them as GNU C89 (`-std=gnu89`), with what GCC 14 and clang 16 made errors
kept as warnings, as they were built when they were written; MSVC needs nothing.

## Changes to the CK sources

Only where they would not build or run on every target:

- config.h: snprintf and vsnprintf mapped to _snprintf and _vsnprintf only for MSVC before 2015, which had no C99 ones (the macros are an error with the Universal CRT)
- audio_esd.c: without <unistd.h>, which nothing there uses: config.h leaves HAVE_UNISTD_H unset, so global.h makes isatty() a macro that breaks the header (Linux) or the header is missing (Windows)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
