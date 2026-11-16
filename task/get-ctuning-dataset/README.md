# get-ctuning-dataset

The inputs of the cBench benchmarks (cTuning MiDataSets, 491 inputs in 23 capsules - one per kind of input,
`20261115.ctuning-midatasets.<kind>.tar.gz`) and the office webcam snapshots of the CK paper (5 sets, their
files published one by one: `dataset.ctuning-image-jpg-fgg-office.day.data_orig.jpg` ...), on demand. The sets
are described by the indexes in `files/` (`indexes` of `_desc.yaml`): every set, its inputs, every file with its
size and SHA-256, and for the published files their published name.

The first use of a set copies or downloads it once into the cMeta cache (one cache entry per set): a capsule is
compared with the SHA-256 of the index and unpacked, published files are fetched one by one; every file is then
compared with the index. The result names the folder, which holds a folder per input - `path_root` - and, when
an input was asked for, its files:

- `path` - its first file (in CK's order: the one a program takes by default)
- `path_entry` - its folder; `files` - its files in CK's order; `number` - for a "number" input

```bash
cx task run get-ctuning-dataset image-ppm -q                     # the set: path_root, entries
cx task run get-ctuning-dataset image-ppm image-ppm-0007 -q      # one input: path, files
cx program run cbench-consumer-jpeg-c cpu --dataset=ctuning-image-ppm/image-ppm-0007 -q
```

Each set is a dataset artifact of this repository (`ctuning-<set>`, made by `import-ck --midatasets=*`) whose
inputs are its sub-datasets: its `_desc.yaml` asks a task for the set (`uses`, `result_from_ctx`) and the
`dataset` task of cmeta-aops takes the input asked for from `path_root` - unless the input is kept with the
artifact (`files/<input>/`: the small inputs of cBench), in which case nothing is fetched. So programs select
their inputs by tags as usual, and `--dataset=ctuning-<set>/<input>` names one. Which task: the index of a set
that names a Hugging Face dataset (`hub:` in `indexes` of `_desc.yaml` - the MiDataSets are
`ctuning/cTuning-MiDataSets`, a folder per kind) makes its datasets use `get-hf-dataset` (cmeta-aops; access
on request on the Hub, `hf auth login` once); the others (the office snapshots, from their Zenodo record) use
this task. The MiDataSets capsules stay the other way: `cx task run get-ctuning-dataset image-ppm
--capsules=<folder>`, or the laptop's setting, serves them from a folder.

## Where the sets come from

`--capsules=<folder, or URL with {name}>` (several separated by `;`), else this machine's setting
(`cx config set task-get-ctuning-dataset --meta.capsules=<folder or URL>`), else the `url` of the set's index
in `indexes` of `_desc.yaml` - its Zenodo record, once published (empty until then). `{name}` stands for the
file name of a capsule or of a published file.
