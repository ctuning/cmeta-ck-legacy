# cMeta CK legacy experiments

Independent archival experiments with the historical MILEPOST GCC and ctuning-cc
pipeline, originally created by Grigori Fursin. Git operations use **ctuning-admin**
and **admin@ctuning.org**.

This repository is not required by the live websites and is not synced to Azure.
It has a separate experimental task UID and selects no website ports by default.

## Extract features from a C program

On any machine with Docker or Podman (Windows, macOS, Linux), with cMeta and its
usual AOps task category installed:

```sh
cx task run extract-milepost-features-legacy,4e719bc8239d4ece --source-file=example.c --output-file=features.json -q
```

The task prepares the original GCC 4.4.4 / ICI 2.05 / MILEPOST 2.1 / XSB 3.2 / CCC
tools once into a container volume and extracts the original 55 static features in a
throwaway Linux container (read-only runtime, no network). It uses no website, port or
credentials. Use GNU89/C89 programs of at most 64 KiB; the program is not executed.
On Linux amd64 with glibc 2.38+, `--runtime-root=<folder>` runs the tools natively.
See the [task guide](task/extract-milepost-features-legacy/README.md).

The binary capsules are deliberately separate from Git source: five public files
`20261114.*.linux-amd64.tar.gz`, published with all their sources and licences in
the archive record [10.5281/zenodo.24246695](https://doi.org/10.5281/zenodo.24246695),
from which the task downloads them by default (`--capsules` names another folder or
URL). The task source contains their SHA-256 checksums. The older private captures are
still accepted (`--capture`); they are not published.

## Git identity

Commits are made with the ctuning-admin account's SSH authentication/signing key.
Transport, author email and signing key are pinned in this repository's local Git
settings. Credentials and `.git` settings are not repository content.
