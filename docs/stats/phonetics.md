# Phonetic helpers

!!! info ""
    **anyts.phonetics**

Functions over the sounds or the letters of the words of a text. A word is given as the collection of its features - the characters of a string, the sounds of a transcription - so the functions see no language: a library chooses the features.

## calc_repetition_index

<!-- --8<-- [start:calc_repetition_index] -->
The repetition index: the number of windows of `window_len` neighbouring words where a feature - a letter or a sound, as a library chooses - occurs in two words or more, summed over the features, to the number expected if the words stood in random order. A window of shuffled words is a sample of them without replacement, so for a feature found in \(K\) of the \(N\) words of the text a window of \(w\) words holds it in two words or more with the hypergeometric probability

$$
P = 1 - \frac{\binom{N-K}{w} + K \binom{N-K}{w-1}}{\binom{N}{w}}
$$

and the expected number is the sum of these probabilities over the features times the \(N - w + 1\) windows. The expectation comes from the text itself, so the index tells whether the repetitions gather in neighbouring words, not how frequent a feature is: it averages to 1 over the orders of the words, and is well above 1 when the repetitions come closer than chance. A word counts a feature once, however often it holds it; `nan` for a text shorter than the window and for a text where no feature is shared by two words.
<!-- --8<-- [end:calc_repetition_index] -->

<!-- --8<-- [start:calc_repetition_index-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str]/list[list[str]] | `-` | Features of every word: a string of its letters or a collection of its sounds |
| `window_len` | int | `-` | Window in words, at least 2 |
| `features` | Collection[str] | `None` | Features to count, all of them by default |
<!-- --8<-- [end:calc_repetition_index-parameters] -->

!!! example "Example"

    ``` python
    from anyts.phonetics import calc_repetition_index

    words = ["sea", "sun", "gas", "fog", "box", "hat"]
    calc_repetition_index(words, 2, {"s"})
    # 2.0
    ```
