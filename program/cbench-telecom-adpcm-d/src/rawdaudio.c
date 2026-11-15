/* testd - Test adpcm decoder */

#include "adpcm.h"
#include <stdio.h>
#include <stdlib.h>

#ifdef XOPENME
#include <xopenme.h>
#endif

struct adpcm_state state;

#define NSAMPLES 1000

char	abuf[NSAMPLES/2];
short	sbuf[NSAMPLES];

int main(int argc, char *argv[])
{
    long ct_repeat=0;
    long ct_repeat_max=1;
    int ct_return=0;
    int n;
    /* cMeta: the input and output files may be given on the command line (an iOS app has no
       redirection, and Windows reads and writes the standard streams in text mode) */
    FILE *ck_in = stdin;
    FILE *ck_out = stdout;

#ifdef XOPENME
  xopenme_init(1,0);
#endif

    if (argc > 1 && (ck_in = fopen(argv[1], "rb")) == NULL) {
	perror(argv[1]);
	exit(1);
    }
    if (argc > 2 && (ck_out = fopen(argv[2], "wb")) == NULL) {
	perror(argv[2]);
	exit(1);
    }

    if (getenv("CT_REPEAT_MAIN")!=NULL) ct_repeat_max=atol(getenv("CT_REPEAT_MAIN"));

#ifdef XOPENME
  xopenme_clock_start(0);
#endif

    while(1) {
        struct adpcm_state current_state = state;

	n = fread(abuf, 1, NSAMPLES/2, ck_in);
	if ( ferror(ck_in) ) {
	    perror("input file");
	    exit(1);
	}
	if ( n == 0 ) break;
  
        /* gfursin */
        for (ct_repeat=0; ct_repeat<ct_repeat_max; ct_repeat++)
        {
	  /* The call to adpcm_decoder modifies the state. We need to make a
	     copy of the state and to restore it before each iteration of the
	     kernel to make sure we do not alter the output of the
	     application. */
          state = current_state;
  	  adpcm_decoder(abuf, sbuf, n*2, &state);  /* modifies state */
	}

	fwrite(sbuf, 1, n*4, ck_out);
    }

#ifdef XOPENME
  xopenme_clock_end(0);

  xopenme_dump_state();
  xopenme_finish();
#endif

    if (ck_out != stdout)
	fclose(ck_out);

    return 0;
}
