# Independent MILEPOST feature extraction

Author: Grigori Fursin.

```sh
cx task run extract-milepost-features-legacy,4e719bc8239d4ece --runtime-root=/path/legacy-runtime --source-file=/path/example.c --output-file=/path/features.json -q
```

The runtime root can instead come from `CMETA_MILEPOST_ROOT`. Direct execution
uses the recovered MILEPOST GCC and ctuning-cc/CCC pipeline without contacting
any website or port. Results contain all 55 original features, values and timings.

Prepare a separate writable runtime on Linux amd64 from the three checked
capsules. Preserve the captures' sibling directory layout:

```text
captures/20261020-153341.recovered-runtime/milepost-runtime.tar.gz
captures/20261020-153341.recovered-runtime/compiler-support.tar.gz
captures/20261020-headers/compiler-headers.tar.gz
```

```sh
python3 /path/cmeta-ck-legacy/task/extract-milepost-features-legacy/src/milepost.py prepare --root=/path/legacy-runtime --capture=/path/captures/20261020-153341.recovered-runtime
```

This verifies the capsule checksums, relocates the copied historical profiles and
makes the installed compiler/header files read-only. Allow about 400 MiB installed,
plus 118 MiB compressed capsules; reserving 1 GiB is comfortable. The original
compiler runs on Linux amd64 with its captured compatibility libraries. On Windows
or macOS, run the same cMeta task inside a compatible Linux container or VM with
these directories mounted. No website installation is needed.

Source must use GNU89/C89 syntax and be at most 64 KiB. Resource limits bound
compilation; no submitted program executes. Temporary source is deleted.

Advanced callers may explicitly select their own `--worker=<cMeta host>` or
`--endpoint=<private service URL>`. Neither is selected automatically. This
experimental task has a different UID from the unchanged live website task.
