# shared-codelet-filter

Codelets of the CK paper repository (reproduce-ck-paper): edge detection of an image: the CK program `shared-codelet-filter` of `ctuning/reproduce-ck-paper`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops).

## Run

```bash
cx program run shared-codelet-filter cpu -q
cx program run shared-codelet-filter --compute=android-cpu --target_tmp=tmp-android-cpu -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `default` | `image,raw-bin,rgb` | `(the first)` | `{qinput_files.data}` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

The sources were written before C99 (K&R declarations, functions used without a declaration):
GCC and clang compile them as GNU C89 (`-std=gnu89`), with what GCC 14 and clang 16 made errors
kept as warnings, as they were built when they were written; MSVC needs nothing.

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
