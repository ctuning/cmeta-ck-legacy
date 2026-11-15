/* A small C89 program for the MILEPOST feature extractor: statistics of an array. */

#include <stdio.h>

int main(void)
{
    int values[8] = {3, -1, 4, 1, -5, 9, 2, -6};
    int i, positives = 0, sum = 0, max = values[0];

    for (i = 0; i < 8; i++) {
        sum += values[i];
        if (values[i] > 0)
            positives++;
        if (values[i] > max)
            max = values[i];
    }

    printf("sum=%d positives=%d max=%d\n", sum, positives, max);
    return 0;
}
