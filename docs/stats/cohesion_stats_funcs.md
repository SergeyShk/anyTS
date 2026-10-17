# Metric functions

!!! info ""
    **anyts.cohesion_stats**

Functions that measure how the sentences of a text are tied together by shared elements, in the manner of Coh-Metrix, and the search of the [connectors](#connectors) that tie them. A sentence is given as the collection of its elements - lemmas of nouns, arguments or content words, values of a feature of its verbs - so the functions see no language: a library chooses the elements.

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
    from anyts.cohesion_stats import calc_overlaps, calc_repetition, count_given

    calc_overlaps([{"cat", "house"}, {"cat", "dog"}, {"bird"}])
    # Overlap(adjacent=0.5, all=0.3333333333333333, prop_adjacent=0.25, prop_all=0.16666666666666666)
    count_given([["cat", "house"], ["cat", "dog"], ["house"]])
    # 2
    calc_repetition([["Pres"], ["Pres", "Past", "Pres"], ["Past"]])
    # 0.5
    ```

## Connectors { #connectors }

<!-- --8<-- [start:ConnectorMatcher] -->
`ConnectorMatcher(connectors)` finds the connectors (discourse markers: *because*, *however*, *on the other hand*) of a dictionary in the sentences of a text. The dictionary gives the class of every connector - causal, adversative, concessive, temporal, additive, conditional or reformulative (`CONNECTOR_CLASSES`) - and its kind, primary or secondary (`CONNECTOR_KINDS`). A connector is matched by the normalized forms of its words, the longest one at every position, without overlaps; a period or a hyphen inside a connector may be split off by the tokenizer (*e.g.* as `e`, `g`). An occurrence is a `Connector`: the number of the sentence `sent`, the positions `start` and `end` of its words in the sentence, the connector `text` as the dictionary writes it, its class `cls` and kind `kind`.

A dictionary that is not a mapping of a phrase to a pair of strings raises `SourceTypeError`, an unknown class or kind `ParameterError`.
<!-- --8<-- [end:ConnectorMatcher] -->

<!-- --8<-- [start:ConnectorMatcher-hooks] -->
The rules of a language are class attributes of a subclass, empty by default:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `normalize(text)` | method | Normalized form of a word and of a connector; the lower case by default |
| `blocked_after`, `blocked_before` | class attributes | Words after or before a connector, by its text, that make it no connector (*before the end*) |
| `blocked_after_pos` | class attribute | Parts of speech of the word after a connector, by its text, that make it no connector |
| `not_at_start` | class attribute | Connectors that do not count at the start of a sentence, where they open a reply (*Well, ...*) |
| `only_after` | class attribute | Connectors that count inside a sentence only after these words |
| `pos_tags`, `pos_extra` | class attributes | Parts of speech of a one-word connector, `CONNECTOR_POS` of Universal Dependencies by default, and those allowed for a word on top of them |
| `not_after_pos` | class attribute | Parts of speech of the previous word that make a one-word connector no connector (a determiner: *the before and the after*) |
| `start_only_pos` | class attribute | Parts of speech of a one-word connector that counts only at the start of a sentence (a capitalized connector tagged as a proper noun) |
| `classes`, `kinds` | class attributes | Classes and kinds of the dictionary; `CONNECTOR_CLASSES` and `CONNECTOR_KINDS` by default |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The words of the lists and the keys of `pos_extra` are normalized forms, while the other lists are keyed by the connector as the dictionary writes it.
<!-- --8<-- [end:ConnectorMatcher-hooks] -->

### find

<!-- --8<-- [start:ConnectorMatcher-find] -->
`find(words, sent_index, pos)` returns the occurrences of the connectors in a sentence in the order of its words. The words are those of one sentence without punctuation, the first one its start. With the parts of speech of the words, a one-word connector counts only with a part of speech of `pos_tags` or of `pos_extra` for its form, never after one of `not_after_pos`, and with one of `start_only_pos` only at the start of the sentence; a word without a part of speech (`None`) passes, and without the parts of speech these rules are skipped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the sentence |
| `sent_index` | int | `0` | Number of the sentence, written into the occurrences |
| `pos` | list[str] | `None` | Parts of speech of the words |

Words that are not a list of strings and parts of speech that are not a list of strings and `None` (the tags `token.pos_` of spaCy, not the numbers `token.pos`) raise `SourceTypeError`, a number of the sentence that is not an integer and parts of speech not as many as the words `ParameterError`.
<!-- --8<-- [end:ConnectorMatcher-find] -->

!!! example "Example"

    ``` python
    from anyts.cohesion_stats import ConnectorMatcher


    class Matcher(ConnectorMatcher):
        blocked_after = {"before": frozenset({"the"})}
        not_after_pos = frozenset({"DET"})


    matcher = Matcher(
        {
            "however": ("adversative", "secondary"),
            "before": ("temporal", "primary"),
            "and": ("additive", "primary"),
            "on the other hand": ("adversative", "secondary"),
        }
    )
    matcher.find("On the other hand he left before the end".split())
    # [Connector(sent=0, start=0, end=4, text='on the other hand', cls='adversative', kind='secondary')]
    matcher.find(["The", "before", "and", "after"], pos=["DET", "ADV", "CCONJ", "ADV"])
    # [Connector(sent=0, start=2, end=3, text='and', cls='additive', kind='primary')]
    ```
