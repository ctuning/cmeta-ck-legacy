# import-ck

Converts programs and datasets of the Collective Knowledge (CK) format into cMeta artifacts of this
repository, by family: cBench, PolyBench/C 3.2 CPU and PolyBench/GPU 1.0 CUDA and OpenCL (CK
`ctuning/ck-ml`), and the codelets of the CK paper repository (`reproduce-ck-paper`). The programs inherit
`template-c-cpu` and the hooks of `template-ck-program` (cmeta-aops) and use its `lib-xopenme`,
`lib-polybench`, `lib-cuda` and `lib-opencl`.
Datasets: one per set of inputs of the indexes of `get-ctuning-dataset` - a kind of cBench input (the cTuning
MiDataSets: `ctuning-adpcm` with its 20 inputs), a set of the office snapshots of the CK paper
(`ctuning-image-jpg-fgg-office`: day, night) - its inputs as sub-datasets (`sub_datasets` of its `_desc.yaml`,
with their files, size, tags, number and CK entry). The small inputs that cBench takes by default
(`local_inputs` of the `datasets` block: `*-0001` ...) are kept with the artifact (`files/<input>/`); the others
come from the set on demand. The CK datasets of a CK repository (`--datasets`) are converted with their files.

```bash
# the programs, from a CK repository (ctuning/ck-ml)
cx task run import-ck <CK repository folder> --programs=cbench-*,polybench-cpu-* \
   --exclude=cbench-automotive-susan,polybench-cpu-gemm -q

# the PolyBench/GPU CUDA and OpenCL kernels; the codelets of the CK paper repository (extracted from the CK home)
cx task run import-ck <CK repository folder> --programs=polybench-cuda-*,polybench-opencl-* -q
cx task run import-ck <reproduce-ck-paper folder> --programs=shared-codelet-* -q

# a dataset per set of inputs (no CK folder needed: the indexes of get-ctuning-dataset); the inputs kept with
# the artifacts are copied from the sets, prepared and checked by get-ctuning-dataset (--capsules: where they are)
cx task run import-ck --midatasets=* --capsules=<folder with the capsules and the published files> -q

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
  not copied: they come from `template-ck-program` of cmeta-aops;
- writes the `output_check:` block of the reference outputs (`cx program run ... --check_output`): the files
  CK compared (`run_correctness_output_files` of the meta, per command when they differ: the files a program
  writes and the standard error it redirected, `tmp-output2.tmp`), what `output_check:` of `_desc.yaml` adds by
  program or by "<program> <command>" (`files` compared too - the standard output where the result is -,
  `skip` for outputs that hold something of the machine or the moment, `why`), and `invariant_of_repeat`
  where CK said the output does not depend on the kernel's repeat. PolyBench/C compares its dump file (CK's
  standard error held the arrays; the patch moved them into `tmp-ck-output-dump.txt`); a family's rules come from
  `output_check_families:` of `_desc.yaml` - PolyBench/GPU compares its standard output without the lines that
  name the device (`ignore_lines`), so its reference says the GPU's result matched the CPU's on any device.

Nothing else of the CK sources changes; the patches are the record of what did.
