# Arithmetic

!!! info ""
    **anyts.utils**

Division and mean that do not fail on empty input, and the entropy of a distribution.

## safe_divide

<!-- --8<-- [start:safe_divide] -->
Divides two numbers and returns `default` for a zero denominator.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `num` | float/int | `-` | Numerator |
| `den` | float/int | `-` | Denominator |
| `default` | float/int | `0` | Value returned for a zero denominator |
<!-- --8<-- [end:safe_divide] -->

## safe_mean

<!-- --8<-- [start:safe_mean] -->
The arithmetic mean of numbers, `default` for no numbers.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `values` | list[float] | `-` | Numbers |
| `default` | float | `nan` | Value returned for no numbers |
<!-- --8<-- [end:safe_mean] -->

## shannon_entropy

<!-- --8<-- [start:shannon_entropy] -->
The Shannon entropy in bits of a distribution given by the count of every value, such as a `Counter`: $-\sum p_i \log_2 p_i$ with $p_i$ the share of a value; 0 for one value, `nan` for no counts; a zero count is left out, as $0 \log_2 0 = 0$.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `counts` | dict[object, int] | `-` | Count of every value |
<!-- --8<-- [end:shannon_entropy] -->
