# Metric functions

The functions know no language: a word is given as its letters (the characters of a string) or the sounds of its transcription, and the classes of the sounds or the features to count come through the parameters.

## CV pattern

!!! info ""
    **anyts.phon_stats.cv_pattern()**

<!-- --8<-- [start:cv_pattern] -->
The CV pattern of a word or a syllable: V for a vowel, C for a consonant, the other sounds (signs, digits, letters of another script) left out.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sounds` | list[str] | `-` | Sounds or letters of the word |
| `vowels` | Collection[str] | `-` | Vowels |
| `consonants` | Collection[str] | `-` | Consonants |
<!-- --8<-- [end:cv_pattern] -->

## Consonant clusters

!!! info ""
    **anyts.phon_stats.consonant_clusters()**

<!-- --8<-- [start:consonant_clusters] -->
The lengths of the consonant clusters of a word in order: a cluster is a run of consonants, a single one included; a sound of `skipped` neither counts nor breaks the run, any other sound breaks it.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sounds` | list[str] | `-` | Sounds or letters of the word |
| `consonants` | Collection[str] | `-` | Consonants |
| `skipped` | Collection[str] | `()` | Sounds that keep a cluster whole, such as a sign that marks the consonant before it |
<!-- --8<-- [end:consonant_clusters] -->

## Hiatuses

!!! info ""
    **anyts.phon_stats.count_hiatus()**

<!-- --8<-- [start:count_hiatus] -->
The number of the hiatuses of a word by its vowels in a row: a run of two vowels or more is one hiatus; a vowel of `glides` after a vowel makes none.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sounds` | list[str] | `-` | Sounds or letters of the word |
| `vowels` | Collection[str] | `-` | Vowels |
| `glides` | Collection[str] | `()` | Vowels that make no hiatus after a vowel, such as a letter that writes a glide and a vowel |
<!-- --8<-- [end:count_hiatus] -->

## Repetition index

!!! info ""
    **anyts.phon_stats.calc_repetition_index()**

<!-- --8<-- [start:calc_repetition_index] -->
The repetition index: the number of windows of `window_len` neighbouring words where a feature (a letter or a sound) occurs in two words or more, summed over the features, divided by the number expected if the words stood in random order. A window of shuffled words is a sample without replacement, so for a feature found in \(K\) of the \(N\) words, a window of \(w\) words holds it in two words or more with the hypergeometric probability

$$
P = 1 - \frac{\binom{N-K}{w} + K \binom{N-K}{w-1}}{\binom{N}{w}}
$$

and the expected number is the sum of these probabilities over the features times the \(N - w + 1\) windows. Since the expectation comes from the text itself, the index shows whether the repetitions gather in neighbouring words, not how frequent a feature is: it averages to 1 over the orders of the words and is well above 1 when the repetitions come closer than chance. A word counts a feature once; the index is `nan` for a text shorter than the window or with no feature shared by two words.
<!-- --8<-- [end:calc_repetition_index] -->

<!-- --8<-- [start:calc_repetition_index-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str]/list[list[str]] | `-` | Features of every word: a string of its letters or a collection of its sounds |
| `window_len` | int | `-` | Window in words, at least 2 |
| `features` | Collection[str] | `None` | Features to count, all of them by default |

Words that are not a list of strings or of collections of strings and features that are not a collection of strings raise `SourceTypeError`, and a `window_len` that is not an integer of at least 2 `ParameterError`.
<!-- --8<-- [end:calc_repetition_index-parameters] -->

## Parameters of the metrics { #check_params }

!!! info ""
    **anyts.phon_stats.check_params()**

<!-- --8<-- [start:PhonStats-check_params] -->
`check_params(window_len, *, messages)` checks the window of the alliteration and the assonance: one that is not an integer of at least 2 raises `ParameterError`.
<!-- --8<-- [end:PhonStats-check_params] -->

!!! example "Example"

    ``` python
    from anyts.phon_stats import calc_repetition_index, consonant_clusters, count_hiatus, cv_pattern

    vowels, consonants = set("aeiou"), set("bcdfghjklmnpqrstvwxyz")
    cv_pattern("strong", vowels, consonants)
    # 'CCCVCC'
    consonant_clusters("strength", consonants)
    # (3, 4)
    count_hiatus("cooperation", vowels)
    # 2
    calc_repetition_index(["sea", "sun", "gas", "fog", "box", "hat"], 2, {"s"})
    # 2.0
    ```
