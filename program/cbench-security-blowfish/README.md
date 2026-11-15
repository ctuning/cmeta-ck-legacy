# cbench-security-blowfish

cBench (MiBench-based, cTuning): the CK program `cbench-security-blowfish` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-security-blowfish cpu --cmd=decode -q
cx program run cbench-security-blowfish cpu --cmd=encode -q
cx program run cbench-security-blowfish --compute=android-cpu --target_tmp=tmp-android-cpu --cmd=decode -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `decode` | `benc,crypto` | `(the first)` | `d {qinput_files.data} tmp-output.tmp 1234567890abcdeffedcba0987654321` |
| `encode` | `enc,crypto` | `(the first)` | `e {qinput_files.data} tmp-output.tmp 1234567890abcdeffedcba0987654321` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- bf.c: the input and output files in binary mode ("rb", "wb"; Windows changed the bytes in text mode)
- bf.c: the xOpenME timer spans the whole loop over the blocks, and its state is written and freed once after it (before, xopenme_finish() ran after every 40-byte block: a double free from the second block)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
