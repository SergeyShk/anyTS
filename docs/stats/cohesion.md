# Cohesion helpers

!!! info ""
    **anyts.cohesion**

Functions that measure how the sentences of a text are tied together by shared elements, in the manner of Coh-Metrix. A sentence is given as the collection of its elements - lemmas of nouns, arguments or content words, values of a feature of its verbs - so the functions see no language: a library chooses the elements.

<!-- --8<-- [start:cohesion-checks] -->
A list of sentences that is a string, a `Doc`, an iterator, a set or a table raises `SourceTypeError`, and so does a sentence that is not a list of strings (`check_words`): a string would be read character by character, an iterator exhausted by the first pass, and spaCy tokens never match, since a token equals only itself. The overlaps (`calc_overlap`, `calc_proportional_overlap`, `calc_overlaps`) compare sets of words and take a sentence as a set too; `count_given` and `calc_repetition` count the words in order and refuse a set.
<!-- --8<-- [end:cohesion-checks] -->

## calc_overlap

<!-- --8<-- [start:calc_overlap] -->
The binary overlap of Coh-Metrix (CRFNO1, CRFAO1, CRFSO1 over the adjacent pairs, CRFNOa, CRFAOa, CRFSOa over all of them): the share of the pairs of sentences that share at least one element; `nan` for a text shorter than two sentences. All the pairs are counted as in `calc_overlaps`, without going through them.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sets` | list[set[str]] | `-` | Elements of every sentence |
| `adjacent` | bool | `True` | Count the adjacent pairs only, otherwise all the pairs |
<!-- --8<-- [end:calc_overlap] -->

## calc_proportional_overlap

<!-- --8<-- [start:calc_proportional_overlap] -->
The proportional overlap of Coh-Metrix (CRFCWO1, CRFCWOa): the Dice coefficient of a pair of sentences averaged over the pairs; `nan` for a text shorter than two sentences. Over all the pairs the sum is computed as in `calc_overlaps`, without going through them.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sets` | list[set[str]] | `-` | Elements of every sentence |
| `adjacent` | bool | `True` | Count the adjacent pairs only, otherwise all the pairs |
<!-- --8<-- [end:calc_proportional_overlap] -->

## dice

<!-- --8<-- [start:dice] -->
The Dice coefficient of two sets:

$$
\frac{2 \times |A \cap B|}{|A| + |B|}
$$

and 0 for two empty sets.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `first` | frozenset[str] | `-` | First set |
| `second` | frozenset[str] | `-` | Second set |
<!-- --8<-- [end:dice] -->

## calc_overlaps

<!-- --8<-- [start:calc_overlaps] -->
The values of `calc_overlap` and `calc_proportional_overlap` over the adjacent and over all the pairs at once, as an `Overlap` named tuple with the fields `adjacent`, `all`, `prop_adjacent` and `prop_all`. The values over all the pairs are computed without going through every pair: the pairs sharing an element are counted over bit masks of the sentences, and the sum of the Dice coefficients over the histograms of the lengths of the sentences holding every element. That sum is added by `math.fsum`, so it does not depend on the order of the elements. Without `proportional` the fields `prop_adjacent` and `prop_all` are `nan`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sets` | list[set[str]] | `-` | Elements of every sentence |
| `proportional` | bool | `True` | Compute the proportional overlap as well |
<!-- --8<-- [end:calc_overlaps] -->

## count_given

<!-- --8<-- [start:count_given] -->
The number of given elements: an element is given when the same lemma was used earlier in any sentence, the current one included; the first occurrence is new.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sents` | list[list[str]] | `-` | Lemmas of every sentence in the order of the text |
<!-- --8<-- [end:count_given] -->

## dominant

<!-- --8<-- [start:dominant] -->
The dominant value: the most frequent one, the first of the equally frequent; `None` for an empty list.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `values` | list[str] | `-` | Values |
<!-- --8<-- [end:dominant] -->

## calc_repetition

<!-- --8<-- [start:calc_repetition] -->
The repetition of the tense and of the mood of Coh-Metrix (SMTEMP): the share of the adjacent pairs of sentences whose verbs have the same dominant value of the feature; a pair where one of the sentences has no verb with the feature is skipped, and without a single such pair the value is `nan`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `sents` | list[list[str]] | `-` | Values of the feature of the verbs of every sentence |
<!-- --8<-- [end:calc_repetition] -->

!!! example "Example"

    ``` python
    from anyts.cohesion import calc_overlaps, calc_repetition, count_given

    calc_overlaps([{"cat", "house"}, {"cat", "dog"}, {"bird"}])
    # Overlap(adjacent=0.5, all=0.3333333333333333, prop_adjacent=0.25, prop_all=0.16666666666666666)
    count_given([["cat", "house"], ["cat", "dog"], ["house"]])
    # 2
    calc_repetition([["Pres"], ["Pres", "Past", "Pres"], ["Past"]])
    # 0.5
    ```
