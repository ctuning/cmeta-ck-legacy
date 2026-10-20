# cMeta CK legacy experiments

Independent archival experiments with the historical MILEPOST GCC and ctuning-cc
pipeline, originally created by Grigori Fursin. Git operations use **ctuning-admin**
and **admin@ctuning.org**.

This repository is not required by the live websites and is not synced to Azure.
It has a separate experimental task UID and selects no website ports by default.

## Extract features from a C program

On compatible Linux amd64, or inside a cMeta Linux container with the prepared
runtime mounted, with cMeta and its usual AOps task category installed:

```sh
cx task run extract-milepost-features-legacy,4e719bc8239d4ece --runtime-root=/path/legacy-runtime --source-file=/path/example.c --output-file=/path/features.json -q
```

Alternatively set `CMETA_MILEPOST_ROOT` once. The direct mode launches the original
GCC 4.4.4 / ICI 2.05 / MILEPOST 2.1 / XSB 3.2 / CCC tools locally. It uses no HTTP
server, website project, Docker socket or website credentials. The result includes
the original 55 static features and JSON values. Use GNU89/C89 programs of at most
64 KiB. The compiled user program is not executed.

Windows and macOS need a compatible Linux amd64 container or VM for these old
binaries. cMeta runs inside that environment using the same command. See the
[task guide](task/extract-milepost-features-legacy/README.md) for preparing the runtime.

Large recovered binary capsules are deliberately separate from Git source. The
private checked captures currently live in
a private result artifact; they can be copied
to another machine without installing or running any website. The task source
contains their required SHA-256 checksums and preserves original software notices.

## Git identity

Commits are made with the ctuning-admin account's SSH authentication/signing key.
Transport, author email and signing key are pinned in this repository's local Git
settings. Credentials and `.git` settings are not repository content.
