/**
 * fdtd-apml.h: This file is part of the PolyBench/C 3.2 test suite.
 *
 *
 * Contact: Louis-Noel Pouchet <pouchet@cse.ohio-state.edu>
 * Web address: http://polybench.sourceforge.net
 */
#ifndef FDTD_APML_H
# define FDTD_AMPL_H

/* Default to STANDARD_DATASET. */
# if !defined(MINI_DATASET) && !defined(SMALL_DATASET) && !defined(LARGE_DATASET) && !defined(EXTRALARGE_DATASET)
#  define STANDARD_DATASET
# endif

/* Do not define anything if the user manually defines the size. */
# if !defined(CZ) && ! defined(CYM) && !defined(CXM)
/* Define the possible dataset sizes. */
#  ifdef MINI_DATASET
#   define CZ 32
#   define CYM 32
#   define CXM 32
#  endif

#  ifdef SMALL_DATASET
#   define CZ 64
#   define CYM 64
#   define CXM 64
#  endif

#  ifdef STANDARD_DATASET /* Default if unspecified. */
#   define CZ 256
#   define CYM 256
#   define CXM 256
#  endif

#  ifdef LARGE_DATASET
#   define CZ 512
#   define CYM 512
#   define CXM 512
#  endif

#  ifdef EXTRALARGE_DATASET
#   define CZ 1000
#   define CYM 1000
#   define CXM 1000
#  endif
# endif /* !N */

# define _PB_CZ POLYBENCH_LOOP_BOUND(CZ,cz)
# define _PB_CYM POLYBENCH_LOOP_BOUND(CYM,cym)
# define _PB_CXM POLYBENCH_LOOP_BOUND(CXM,cxm)

# ifndef DATA_TYPE
#  define DATA_TYPE double
# endif

/* The printf format of DATA_TYPE (cMeta, task::import-ck: MSVC refuses "#if DATA_TYPE == double").
 * Two levels of macros expand DATA_TYPE before ## pastes it into the name of its format:
 * -DDATA_TYPE=double -> DATA_TYPE_double_FMT -> "%0.2lf " (C89, MSVC, GCC, Clang). */
# define DATA_TYPE_double_FMT "%0.2lf "
# define DATA_TYPE_float_FMT  "%0.2f "
# define DATA_TYPE_long_FMT   "%ld "
# define DATA_TYPE_int_FMT    "%d "

# define DATA_PRINTF_MODIFIER_PASTE(t) DATA_TYPE_ ## t ## _FMT
# define DATA_PRINTF_MODIFIER_EXPAND(t) DATA_PRINTF_MODIFIER_PASTE(t)
# define DATA_PRINTF_MODIFIER DATA_PRINTF_MODIFIER_EXPAND(DATA_TYPE)

#endif /* !FDTD_APML */
