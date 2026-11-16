# polybench-cuda-3dconv

PolyBench/GPU 1.0 CUDA (Ohio State University, University of Delaware), CK version: the CK program `polybench-cuda-3dconv` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`, `lib-cuda`).

## Run

```bash
cx program run polybench-cuda-3dconv cuda -q
```

**The check:** the program computes the result on the CPU too and prints how many elements of the
GPU's result differ from it beyond the threshold of the source (`Non-Matching CPU-GPU Outputs
Beyond Error Threshold of <p> Percent: <n>`, on standard output; 0 is right). The CK version had
that CPU reference in a comment (so its count compared with memory never computed);
`--compile.check=no` builds it so again. The sizes are CK's (compile variables).

It runs the kernel on the GPU (`cuda`), with CUDA 11, 12 or 13 (`--use.nvcc.version=<v>`); the GPU
and its compute capability are printed first.

Sizes: CK's by default (DIM_THREAD_BLOCK_X=8, DIM_THREAD_BLOCK_Y=8, NI=64, NJ=64, NK=64),
the result checked against the CPU's. `--compile.size=mini|small|standard|large|extralarge`
takes the sizes of PolyBench's header instead;
`--compile.n=<N>` makes every dimension N (square arrays);
`--compile.precision=float|double` sets `DATA_TYPE`; `--compile.d.<NAME>=<value>` any define. Each
choice is a build of its own, and part of the key of its reference outputs.

```bash
cx program run polybench-cuda-3dconv cuda --compile.size=large -q
cx program run polybench-cuda-3dconv cuda --compile.n=512 --compile.precision=float -q
```

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`); `--calibrate[=<seconds>]` raises the
repeat until the run lasts about the target (4 s, as CK did; at most `--calibrate_max=10` rounds).
Standard output and error go to `tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on
iOS); the times of the kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).
The summary printed after the run names the parameters and the defines of the build; `--check_output`
compares the outputs with the reference of the same command, input and parameters (`program.output`),
or records one.

## Changes to the CK sources

Only where they would not build or run on every target:

- 3DConvolution.cu: from CUDA 13 on (CUDART_VERSION >= 13000) cudaDeviceSynchronize() for cudaThreadSynchronize() and the compute mode from cudaDeviceGetAttribute - CUDA 13 removed both; CUDA 11 and 12 keep the original calls
- 3DConvolution.cu: the arrays of main() are allocated zeroed (calloc): kernels that add into an array main() sends to the GPU uninitialized (3mm, atax, bicg, gesummv) gave results that depended on what the memory held
- 3DConvolution.cu: the CPU reference of main() that CK commented out is compiled with CK_CPU_CHECK (defined unless --compile.check=no), so that "Non-Matching CPU-GPU Outputs" compares the GPU's result with the CPU's

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
