# get-ctuning-dataset

The full inputs of the cBench benchmarks (cTuning MiDataSets, 491 inputs, 23 capsules - one per kind
of input, `20261115.ctuning-midatasets.<kind>.tar.gz`) and the office webcam snapshots of the CK paper
repository (10 inputs, `20261115.ck-office-snapshots.datasets.tar.gz`), on demand. Each set has its
index in `files/` (`indexes` of `_desc.yaml`). The first use of an input copies or downloads its capsule
once into the cMeta cache (one cache entry per capsule), compares its SHA-256 and the SHA-256 of every
file with the index and unpacks it; the result names the files of the entry asked for:

- `path` - its first file (in CK's order: the one a program takes by default)
- `path_entry` - its folder; `files` - its files in CK's order; `number` - for a "number" entry

```bash
cx task run get-ctuning-dataset image-ppm image-ppm-0007 -q
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm-0007 -q
```

Each entry is also a dataset artifact of this repository (`ctuning-<entry>`, made by `import-ck
--midatasets=*`) whose `_desc.yaml` asks this task for its files, so programs select the inputs by tags
as usual.

## Where the capsules come from

`--capsules=<folder, or URL with {name}>`, else this machine's setting
(`cx config set task-get-ctuning-dataset --meta.capsules=<folder or URL>`), else the `url` of the
capsule's set in `indexes` of `_desc.yaml` - its Zenodo record, once published (empty until then).
