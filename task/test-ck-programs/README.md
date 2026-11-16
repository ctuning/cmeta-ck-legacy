# test-ck-programs

Runs every command of the converted CK programs (cBench, PolyBench/C) on one target, records what each
run did - its status, its time, the kernel time measured by xOpenME, the SHA-256 of every output file -
and compares the records of several targets, compilers or hosts.

```bash
cx task run test-ck-programs --out=windows-msvc.json -q
cx task run test-ck-programs "--extra=--use.compiler-c.name=clang" --out=windows-clang.json -q
cx task run test-ck-programs --compute=android-cpu --out=android.json -q
cx task run test-ck-programs --programs=cbench-* --all_datasets --out=all-inputs.json -q   # every input
cx task run test-ck-programs --compare=windows-msvc.json,windows-clang.json,android.json -q
```

Each run is `cx program run <program> --compute=<target> [--cmd=<command>] [--dataset=<alias>] -q` in a
process of its own, with standard input closed and a time limit (`--timeout`, 900 s); its output goes
to `<out>-logs/`. `--compile_only` only builds (`cx program compile`).

The comparison says, per program and command, whether the outputs are the same everywhere; it reads
Windows' line ends (`\r\n`) as `\n` and every spelling of NaN (`-nan(ind)`, `-nan`, `nan`) as one, and
names - without comparing them - the outputs that hold something of the host or of the moment
(`host_dependent` in `_desc.yaml`: the path of an input, the time of a signature, progress on standard
error). When outputs differ, it shows which records agree with which (A, B ...).

A run is also checked when the program declares what it must print (`checks` in `_desc.yaml`: a file of the
build folder, a regular expression, the value its group must have): the PolyBench/GPU programs (CUDA,
OpenCL) compare the GPU's result with the CPU's and print how many values differ beyond the threshold of
the source - a run whose count is not 0 is `check failed` (the record keeps the count). Runs built without
the CPU reference (`--extra=--compile.check=no`, as CK built them) are not checked.
