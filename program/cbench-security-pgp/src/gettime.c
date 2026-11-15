/*
 *	Gettimeofday.  Simulate as much as possible.  Only accurate
 *	to nearest second.  tzp is ignored.  Derived from an old
 *	emacs implementation.
 */

#include <sys/types.h>
#if defined(WINDOWS)
#include <time.h>
#include <winsock2.h>
#else
#include <sys/time.h>
#endif

/* cMeta: only where the C library has no gettimeofday() */
#if defined(WINDOWS)
gettimeofday (tp, tzp)
     struct timeval *tp;
     struct timezone *tzp;
{
#if !defined(WINDOWS)
  extern long time ();
#endif

  tp->tv_sec = time ((long *)0);
  tp->tv_usec = 0;
}
#endif
