# import-ck

Converts programs and datasets of the Collective Knowledge (CK) format into cMeta artifacts of this
repository, by family: cBench, PolyBench/C 3.2 CPU and PolyBench/GPU 1.0 CUDA and OpenCL (CK
`ctuning/ck-ml`), and the codelets of the CK paper repository (`reproduce-ck-paper`). The programs inherit
`template-c-cpu` and the hooks of `template-ck-program` (cmeta-aops) and use its `lib-xopenme`,
`lib-polybench`, `lib-cuda` and `lib-opencl`.
Datasets: the small inputs (with their files), and a dataset per entry of the capsules of
`get-ctuning-dataset` (the cTuning MiDataSets, the office snapshots of the CK paper; files on demand).

```bash
# the programs and the small inputs, from a CK repository (ctuning/ck-ml)
cx task run import-ck <CK repository folder> --programs=cbench-*,polybench-cpu-* --datasets=* \
   --exclude=cbench-automotive-susan,polybench-cpu-gemm,tensor-*,image-jpeg-dnn-*,image-ppm-dnn-*,image-jpeg-fgg,adpcm-0001,image-pgm-0001,image-pgm-from-pamela-100 -q

# the PolyBench/GPU CUDA and OpenCL kernels; the codelets of the CK paper repository (extracted from the CK home)
cx task run import-ck <CK repository folder> --programs=polybench-cuda-*,polybench-opencl-* -q
cx task run import-ck <reproduce-ck-paper folder> --programs=shared-codelet-* -q

# a dataset per entry of the capsules (no CK folder needed: the indexes of get-ctuning-dataset)
cx task run import-ck --midatasets=* -q

# LICENSES.md at the root: the licence of every program (licenses_info of _desc.yaml) and dataset
cx task run import-ck --licenses_md -q
```

`--force` remakes the artifacts of this repository (a dataset with files of its own is always kept),
`--dry_run` only says what would be made. The excluded ones exist in cmeta-aops already, or are not
cBench inputs.

## What it does to a CK program

- copies every file of the CK entry into `src/`;
- PolyBench: the printf format of `DATA_TYPE` by token pasting (MSVC refuses `#if DATA_TYPE == double`)
  and `print_array` writing into `tmp-ck-output-dump.txt` (an iOS app has no redirection);
- applies `files/patches/<CK program>.patch` - a unified diff whose `# ` lines say what it changes and
  why; each fixes something that does not build or run on one of the targets (or a defect found by
  comparing the outputs of the targets);
- PolyBench/GPU: from CUDA 13 on (`CUDART_VERSION >= 13000`), `cudaDeviceSynchronize()` for
  `cudaThreadSynchronize()` and the compute mode from `cudaDeviceGetAttribute`, which CUDA 13 removed;
  CUDA 11 and 12 keep the original calls (a block in front of `GPU_argv_init()`);
- PolyBench/GPU OpenCL: the kernel (`"$#src_path#$<kernel>.cl"` in CK's command line) becomes a run file of
  the program (`ck_run_files`: copied into the run folder, pushed to a device) named on the command line;
  the arrays of platform and device IDs hold the 15 IDs the OpenCL calls may write (CK allocated
  `sizeof(id) * index + 1` bytes: a heap overflow with two OpenCL platforms or more); the platform and
  device come from the hooks (`ck_opencl_device`); `CL_TARGET_OPENCL_VERSION=120`, the API of the codes;
  `android-gpu` too (a stub of `libOpenCL.so` to link, the device's own at run time);
- PolyBench/GPU (CUDA and OpenCL): the CPU reference that CK commented out in `main()` is compiled under
  `#ifdef CK_CPU_CHECK` (the hooks define it unless `--compile.check=no`), so "Non-Matching CPU-GPU Outputs"
  is a check - and `test-ck-programs` fails a run whose count is not 0; the arrays of `main()` are allocated
  zeroed (`calloc`): the kernels of 3mm, atax, bicg and gesummv add into arrays that `main()` sent to the GPU
  uninitialized;
- copies licence files the CK entry lacks (`licenses:` in `_desc.yaml`, `files/licenses/`: the GPLv2 and
  a statement for PolyBench/C 3.2, a notice for PolyBench/GPU 1.0, libtiff's for tiff2rgba, the CK paper
  repository's BSD-3-Clause for the codelets) and writes the licence into the program's `_desc.yaml`
  (`license`: name, SPDX identifier when there is one, the file of its text - `licenses_info`);
- writes `_desc.yaml` from the CK meta (`build_compiler_vars`, `run_cmds`, `dataset_tags`, outputs),
  with the overrides of `programs:` in `_desc.yaml` (dataset tags where CK took any dataset, GNU C89 for
  sources written before C99, run files ...), `README.md` and a test script per target; the hooks are
  not copied: they come from `template-ck-program` of cmeta-aops.

Nothing else of the CK sources changes; the patches are the record of what did.
