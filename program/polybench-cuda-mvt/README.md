# polybench-cuda-mvt

PolyBench/GPU 1.0 CUDA (Ohio State University, University of Delaware), CK version: the CK program `polybench-cuda-mvt` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`, `lib-cuda`).

## Run

```bash
cx program run polybench-cuda-mvt cuda -q
```

**The check:** the program computes the result on the CPU too and prints how many elements of the
GPU's result differ from it beyond the threshold of the source (`Non-Matching CPU-GPU Outputs
Beyond Error Threshold of <p> Percent: <n>`, on standard output; 0 is right). The CK version had
that CPU reference in a comment (so its count compared with memory never computed);
`--compile.check=no` builds it so again. The sizes are CK's (compile variables).

It runs the kernel on the GPU (`cuda`), with CUDA 11, 12 or 13 (`--use.nvcc.version=<v>`); the GPU
and its compute capability are printed first.

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- mvt.cu: from CUDA 13 on (CUDART_VERSION >= 13000) cudaDeviceSynchronize() for cudaThreadSynchronize() and the compute mode from cudaDeviceGetAttribute - CUDA 13 removed both; CUDA 11 and 12 keep the original calls
- mvt.cu: the arrays of main() are allocated zeroed (calloc): kernels that add into an array main() sends to the GPU uninitialized (3mm, atax, bicg, gesummv) gave results that depended on what the memory held
- mvt.cu: the CPU reference of main() that CK commented out is compiled with CK_CPU_CHECK (defined unless --compile.check=no), so that "Non-Matching CPU-GPU Outputs" compares the GPU's result with the CPU's

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
