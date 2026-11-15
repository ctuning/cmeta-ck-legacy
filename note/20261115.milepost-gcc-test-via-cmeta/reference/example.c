int sum_positive(int *values, int count)
{
    int total = 0;
    int i;
    for (i = 0; i < count; ++i)
        if (values[i] > 0)
            total += values[i];
    return total;
}
