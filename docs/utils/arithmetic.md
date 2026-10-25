# Arithmetic

Division and mean that do not fail on empty input, and the entropy of a distribution.

## Safe division { #safe_divide }

<!-- --8<-- [start:safe_divide] -->
``` {.python .signature}
safe_divide(num, den, default=0)
```

Divides two numbers and returns `default` for a zero denominator.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `num` | `float` / `int` | - | Numerator |
| `den` | `float` / `int` | - | Denominator |
| `default` | `float` / `int` | `0` | Value returned for a zero denominator |
<!-- --8<-- [end:safe_divide] -->

=== "Code"

    ``` python
    from anyts.utils import safe_divide

    safe_divide(3, 4), safe_divide(3, 0), safe_divide(3, 0, default=float("nan"))
    ```

=== "Result"

    ```
    (0.75, 0, nan)
    ```

## Safe mean { #safe_mean }

<!-- --8<-- [start:safe_mean] -->
``` {.python .signature}
safe_mean(values, default=nan)
```

The arithmetic mean of numbers, `default` for no numbers; the numbers may come from an iterator or an array.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `values` | `Iterable[float]` | - | Numbers |
| `default` | `float` | `nan` | Value returned for no numbers |
<!-- --8<-- [end:safe_mean] -->

=== "Code"

    ``` python
    from anyts.utils import safe_mean

    safe_mean([1, 2, 4]), safe_mean(iter([])), safe_mean([], default=0.0)
    ```

=== "Result"

    ```
    (2.3333333333333335, nan, 0.0)
    ```

## Shannon entropy { #shannon_entropy }

<!-- --8<-- [start:shannon_entropy] -->
``` {.python .signature}
shannon_entropy(counts)
```

The Shannon entropy in bits of a distribution given by the count of every value, such as a `Counter`, with $p_i$ the share of a value:

$$
-\sum_i p_i \log_2 p_i
$$

One value gives 0, no counts or only zero ones `nan`; a zero count is left out, as $0 \log_2 0 = 0$.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `counts` | `dict[object, int]` | - | Count of every value |

A negative, `nan` or infinite count raises `SourceError`.
<!-- --8<-- [end:shannon_entropy] -->

=== "Code"

    ``` python
    from collections import Counter

    from anyts.utils import shannon_entropy

    (
        shannon_entropy({"a": 2, "b": 2}),
        shannon_entropy(Counter(["the", "cat", "the"])),
        shannon_entropy({}),
    )
    ```

=== "Result"

    ```
    (1.0, 0.9182958340544896, nan)
    ```
