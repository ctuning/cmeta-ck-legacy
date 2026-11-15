# cbench-consumer-lame

cBench (MiBench-based, cTuning): the CK program `cbench-consumer-lame` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-consumer-lame cpu -q
cx program run cbench-consumer-lame --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `default` | `wav,audio` | `(the first)` | `{qinput_files.data} tmp-output.tmp` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- quantize-pvt.c: the MSVC inline assembly (x87) only for 32-bit x86 (_M_IX86); 64-bit MSVC has no inline assembler and takes the C code, as every other compiler does
- id3tag.c: the unset genre is the byte 255 put into the 1-byte field; strcpy of "ÿ" (two bytes in the UTF-8 CK source, and the NUL) wrote past it, which macOS stops (_FORTIFY_SOURCE: SIGTRAP)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
