# cbench-security-rijndael

cBench (MiBench-based, cTuning): the CK program `cbench-security-rijndael` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`).

## Run

```bash
cx program run cbench-security-rijndael cpu --cmd=decode -q
cx program run cbench-security-rijndael cpu --cmd=encode -q
cx program run cbench-security-rijndael --compute=android-cpu --target_tmp=tmp-android-cpu --cmd=decode -q
```

The input is a `dataset` artifact selected by tags (with `-q`, the first; without it, a menu):
`--dataset=<alias>` picks one, `--dataset_file=<file name or path>` a file of it or any local file.

| Command | Dataset tags | File | Command line after the executable |
|---|---|---|---|
| `decode` | `enc,crypto` | `(the first)` | `{qinput_files.data} tmp-output.tmp d 1234567890abcdeffedcba09876543211234567890abcdeffedcba0987654321` |
| `encode` | `doc,txt` | `data.txt` | `{qinput_files.data} tmp-output.tmp e 1234567890abcdeffedcba09876543211234567890abcdeffedcba0987654321` |

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- aesxam.c: the IV and padding generator in 32-bit arithmetic as on the machines it was written for (unsigned long is 64 bits on Linux, macOS and Android, and its 8 bytes were stored into a 4-byte array), and the file length by ftell (fgetpos wrote a whole fpos_t, 16 bytes with glibc, into an unsigned long); the output was different with every compiler
- aes.h: the 32-bit word of AES as unsigned int, as its comment asks ("must be a 32-bit storage unit"; unsigned long is 64 bits on Linux, macOS and Android)

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
