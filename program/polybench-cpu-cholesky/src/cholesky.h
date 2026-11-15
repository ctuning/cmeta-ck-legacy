/**
 * cholesky.h: This file is part of the PolyBench/C 3.2 test suite.
 *
 *
 * Contact: Louis-Noel Pouchet <pouchet@cse.ohio-state.edu>
 * Web address: http://polybench.sourceforge.net
 */
#ifndef CHOLESKY_H
# define CHOLESKY_H

/* Default to STANDARD_DATASET. */
# if !defined(MINI_DATASET) && !defined(SMALL_DATASET) && !defined(LARGE_DATASET) && !defined(EXTRALARGE_DATASET)
#  define STANDARD_DATASET
# endif

/* Do not define anything if the user manually defines the size. */
# if !defined(N)
/* Define the possible dataset sizes. */
#  ifdef MINI_DATASET
#   define N 32
#  endif

#  ifdef SMALL_DATASET
#   define N 128
#  endif

#  ifdef STANDARD_DATASET /* Default if unspecified. */
#   define N 1024
#  endif

#  ifdef LARGE_DATASET
#   define N 2000
#  endif

#  ifdef EXTRALARGE_DATASET
#   define N 4000
#  endif
# endif /* !N */

# define _PB_N POLYBENCH_LOOP_BOUND(N,n)

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

#endif /* !CHOLESKY */
