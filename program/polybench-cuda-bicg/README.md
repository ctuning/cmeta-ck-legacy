# polybench-cuda-bicg

PolyBench/GPU 1.0 CUDA (Ohio State University, University of Delaware), CK version: the CK program `polybench-cuda-bicg` of `ctuning/ck-ml`, converted to cMeta by
`task::import-ck` of this repository. It inherits `template-c-cpu` and the hooks of
`template-ck-program` (both in cmeta-aops) and uses the run-time libraries of cmeta-aops
(`lib-xopenme`, `lib-polybench`, `lib-cuda`).

## Run

```bash
cx program run polybench-cuda-bicg cuda -q
```

It runs the kernel on the GPU (`cuda`) and prints how many results differ from the CPU's
(`Non-Matching CPU-GPU Outputs ...` on standard output); the sizes are CK's (compile
variables), the GPU and its compute capability are printed first.

`--repeat=<n>` repeats the kernel n times (`CT_REPEAT_MAIN`). Standard output and error go to
`tmp-output1.tmp` and `tmp-output2.tmp` of the build folder (not on iOS); the times of the
kernel, from xOpenME, are in the result (`stats-xopenme`, `tmp-ck-timer.json`).

## Changes to the CK sources

Only where they would not build or run on every target:

- bicg.cu: cudaDeviceSynchronize() for cudaThreadSynchronize(), which CUDA 13 removed (the same since CUDA 4)
- bicg.cu: the compute mode of the GPU from cudaDeviceGetAttribute, as CUDA 13 removed cudaDeviceProp::computeMode

## Licence

The sources keep the licence of their authors: see `src/LICENSE*` or `src/COPYRIGHT` and the headers
of the sources (THIRD-PARTY.md of this repository); the cMeta description and hooks are Apache-2.0.
