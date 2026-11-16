# polybench-opencl-mvt

PolyBench/GPU 1.0 OpenCL (Ohio State University, University of Delaware), CK version: the CK program `polybench-opencl-mvt` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`, `lib-opencl`).

## Run

```bash
cx program run polybench-opencl-mvt android-gpu -q
cx program run polybench-opencl-mvt --compute=android-gpu --target_tmp=tmp-android-gpu -q
```

It runs the kernel (the `.cl` file, built by the OpenCL driver at run time) on an OpenCL device:
with `opencl`, the first GPU the `opencl` target finds, or `--opencl_device=<number or a word of
its name>` (with `--opencl_platform=<number>`), e.g. `--opencl_device=intel`; with `android-gpu`,
the GPU of the Android device (its own libOpenCL.so). It prints the platform and the device.

**The check:** the program computes the result on the CPU too and prints how many elements of the
GPU's result differ from it beyond the threshold of the source (`Non-Matching CPU-GPU Outputs
Beyond Error Threshold of <p> Percent: <n>`, on standard output; 0 is right). The CK version had
that CPU reference in a comment (so its count compared with memory never computed);
`--compile.check=no` builds it so again. The sizes are CK's (compile variables).

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- mvt.c: the arrays of OpenCL platform and device IDs hold the 15 IDs clGetPlatformIDs and clGetDeviceIDs may write (they had sizeof(id) * index + 1 bytes: a heap overflow with two platforms or devices or more)
- mvt.c: the arrays of main() are allocated zeroed (calloc): kernels that add into an array main() sends to the GPU uninitialized (3mm, atax, bicg, gesummv) gave results that depended on what the memory held
- mvt.c: the CPU reference of main() that CK commented out is compiled with CK_CPU_CHECK (defined unless --compile.check=no), so that "Non-Matching CPU-GPU Outputs" compares the GPU's result with the CPU's
- mvt.cl: the kernels' DATA_TYPE is float, as the host's (CK: DATA_TYPE=float); in double they read and wrote past the buffers the host made for floats, and reading the result back failed

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
