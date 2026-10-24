# Cohesion statistics

``` {.python .signature}
CohesionStats(source, sents_extractor=None, connectors=None)
```

<!-- --8<-- [start:CohesionStats] -->
The cohesion statistics of a text in the manner of Coh-Metrix: the overlap of the sentences, the givenness, the temporal cohesion and the connectors of a dictionary. The sentences are compared by lemmas. The data source is a `Doc` object of [spaCy](https://github.com/explosion/spaCy) with the parts of speech and the lemmas, split into sentences by its boundaries, or by the sentence extractor over its text when one is given or the `Doc` has none.

Raises:

- `SourceTypeError` - an extractor of another type, a source that is not a `Doc`, connectors that are not a dictionary of phrases and pairs of strings;
- `SourceError` - a source without parts of speech, lemmas or words;
- `ParameterError` - an unknown class or kind of a connector.
<!-- --8<-- [end:CohesionStats] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.cohesion_stats import CohesionStats


    class English(CohesionStats):
        @classmethod
        def load_connectors(cls):
            return {"however": ("adversative", "secondary")}


    # The cat slept. However, the cat woke.
    doc = Doc(
        spacy.blank("en").vocab,
        words=["The", "cat", "slept", ".", "However", ",", "the", "cat", "woke", "."],
        spaces=[True, True, False, True, False, True, True, True, False, False],
        pos=["DET", "NOUN", "VERB", "PUNCT", "ADV", "PUNCT", "DET", "NOUN", "VERB", "PUNCT"],
        lemmas=["the", "cat", "sleep", ".", "however", ",", "the", "cat", "wake", "."],
        morphs=["", "", "Aspect=Perf|Tense=Past", "", "", "", "", "", "Aspect=Perf|Tense=Past", ""],
        sent_starts=[True, False, False, False, True, False, False, False, False, False],
    )
    stats = English(doc)
    stats.print_stats()
    ```

=== "Result"

    ```
                               Statistic                            |  Value
    ---------------------------------------------------------------------------
    Noun overlap in adjacent sentences                              |   1.00
    Noun overlap in all pairs of sentences                          |   1.00
    Argument overlap in adjacent sentences                          |   1.00
    Argument overlap in all pairs of sentences                      |   1.00
    Content word overlap in adjacent sentences                      |   1.00
    Content word overlap in all pairs of sentences                  |   1.00
    Share of shared content words in adjacent sentences             |   0.40
    Share of shared content words in all pairs of sentences         |   0.40
    Share of pronouns                                               |   0.00
    Ratio of pronouns to nouns                                      |   0.00
    Share of demonstratives                                         |   0.00
    Share of content words seen before                              |   0.20
    Repetition of the tense in adjacent sentences                   |   1.00
    Repetition of the aspect in adjacent sentences                  |   1.00
    Temporal cohesion                                               |   1.00
    Connectors per 1000 words                                       |  142.86
    Connectors linking a sentence to the ones before per 1000 words |  142.86
    Connectors linking the parts of a sentence per 1000 words       |   0.00
    Causal connectors per 1000 words                                |   0.00
    Adversative connectors per 1000 words                           |  142.86
    Concessive connectors per 1000 words                            |   0.00
    Temporal connectors per 1000 words                              |   0.00
    Additive connectors per 1000 words                              |   0.00
    Conditional connectors per 1000 words                           |   0.00
    Reformulative connectors per 1000 words                         |   0.00
    Primary connectors per 1000 words                               |   0.00
    Secondary connectors per 1000 words                             |  142.86
    ```

## Parameters

<!-- --8<-- [start:CohesionStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `Doc` | - | Data source: a `Doc` with the parts of speech and the lemmas, or what `analyze` reads |
| `sents_extractor` | `SentsExtractor` | `None` | Sentence extraction tool; given here, it splits a `Doc` by its text whatever its boundaries |
| `connectors` | `dict[str, tuple[str, str]]` | `None` | Class and kind by connector; those of `load_connectors` by default |
<!-- --8<-- [end:CohesionStats-parameters] -->

## Attributes

<!-- --8<-- [start:CohesionStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `words`, `lemmas` | `tuple[tuple[str]]` | Words and lemmas of every sentence with words |
| `n_sents`, `n_words` | `int` | Numbers of the sentences with words and of the words |
| `n_paragraphs` | `int` | Number of the paragraphs, the parts of the text between blank lines |
| `n_nouns`, `n_pronouns`, `n_demonstratives`, `n_content_words` | `int` | Numbers of the words by kind |
| `n_given` | `int` | Number of the content words whose lemma was used before |
| `n_connectors`, `connector_spans`, `c_connectors` | `int`, `tuple[Connector]`, `dict[str, int]` | Number of the connectors, their occurrences and their number by connector |
| `n_inter_connectors` | `int` | Number of the inter-sentential connectors |
<!-- --8<-- [end:CohesionStats-attributes] -->

=== "Code"

    ``` python
    stats.connector_spans
    stats.c_connectors
    ```

=== "Result"

    ```
    (Connector(sent=1, start=0, end=1, text='however', cls='adversative', kind='secondary'),)
    {'however': 1}
    ```

## Metrics

<!-- --8<-- [start:CohesionStats-metrics] -->
Every metric is an attribute of the object, computed when it is created; `get_stats` gives those of `stats_desc`, all but `mood_repetition` by default. The functions of the cards take a sentence as the collection of its elements - lemmas of nouns, arguments or content words, values of a feature of its verbs - and see no language.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`noun_overlap_adjacent`](#overlap) | Share of the adjacent pairs of sentences sharing a noun | 0-1, `nan` for one sentence | Neighbouring sentences tied tighter |
| [`noun_overlap_all`](#overlap) | Share of all the pairs of sentences sharing a noun | 0-1, `nan` for one sentence | The whole text tied tighter |
| [`argument_overlap_adjacent`](#overlap) | Share of the adjacent pairs sharing a noun or a pronoun | 0-1, `nan` for one sentence | Neighbouring sentences tied tighter |
| [`argument_overlap_all`](#overlap) | Share of all the pairs sharing a noun or a pronoun | 0-1, `nan` for one sentence | The whole text tied tighter |
| [`content_overlap_adjacent`](#overlap) | Share of the adjacent pairs sharing a content word | 0-1, `nan` for one sentence | Neighbouring sentences tied tighter |
| [`content_overlap_all`](#overlap) | Share of all the pairs sharing a content word | 0-1, `nan` for one sentence | The whole text tied tighter |
| [`content_overlap_prop_adjacent`](#proportional_overlap) | Mean share of the shared content words (Dice) in the adjacent pairs | 0-1, `nan` for one sentence | More words shared by neighbours |
| [`content_overlap_prop_all`](#proportional_overlap) | Mean share of the shared content words (Dice) in all the pairs | 0-1, `nan` for one sentence | More words shared across the text |
| [`noun_overlap_2_sent`](#forward_overlap) | Share of the nouns of a sentence repeated in one of the next two | 0-1, `nan` for fewer than three sentences | More nouns carried on |
| [`argument_overlap_2_sent`](#forward_overlap) | Share of the arguments of a sentence repeated in one of the next two | 0-1, `nan` for fewer than three sentences | More arguments carried on |
| [`content_overlap_2_sent`](#forward_overlap) | Share of the content words of a sentence repeated in one of the next two | 0-1, `nan` for fewer than three sentences | More content words carried on |
| [`noun_overlap_para`](#forward_overlap) | Share of the nouns of a paragraph repeated in the next one | 0-1, `nan` for one paragraph | More nouns carried to the next paragraph |
| [`argument_overlap_para`](#forward_overlap) | Share of the arguments of a paragraph repeated in the next one | 0-1, `nan` for one paragraph | More arguments carried to the next paragraph |
| [`content_overlap_para`](#forward_overlap) | Share of the content words of a paragraph repeated in the next one | 0-1, `nan` for one paragraph | More content words carried to the next paragraph |
| [`p_pronouns`](#pronouns) | Share of the pronouns among the words | 0-1 | More reference by pronouns |
| [`pronoun_noun_ratio`](#pronouns) | Ratio of the pronouns to the nouns | 0 and above, `nan` without nouns | More pronouns per noun |
| [`p_demonstratives`](#pronouns) | Share of the demonstratives among the words | 0-1 | More pointing back |
| [`p_given`](#given) | Share of the content words whose lemma was used before in the text | 0-1, `nan` without content words | More given information |
| [`tense_repetition`](#temporal_cohesion) | Share of the adjacent pairs of sentences with the same dominant tense | 0-1, `nan` without two adjacent sentences with the feature | A steadier tense |
| [`mood_repetition`](#temporal_cohesion) | Share of the adjacent pairs with the same dominant mood | 0-1, `nan` without two adjacent sentences with the feature | A steadier mood |
| [`aspect_repetition`](#temporal_cohesion) | Share of the adjacent pairs with the same dominant aspect | 0-1, `nan` without two adjacent sentences with the feature | A steadier aspect |
| [`temporal_cohesion`](#temporal_cohesion) | Mean of the repetitions of `temporal_features` | 0-1, `nan` when one of them is `nan` | A steadier time frame |
| [`connectors`](#connectors) | Connectors per 1000 words | 0-1000 | More explicit links |
| [`connectors_inter`](#connectors) | Inter-sentential connectors per 1000 words | 0-1000 | More links to the sentences before |
| [`connectors_intra`](#connectors) | Intra-sentential connectors per 1000 words | 0-1000 | More links inside the sentences |
| [`connectors_<class>`, `connectors_<kind>`](#connectors) | Connectors of a class or a kind of the matcher per 1000 words | 0-1000 | More links of the class or the kind |
<!-- --8<-- [end:CohesionStats-metrics] -->

<div class="metric-card" markdown>

### Binary overlap { #overlap }

`noun_overlap_adjacent` · `noun_overlap_all` · `argument_overlap_adjacent` · `argument_overlap_all` · `content_overlap_adjacent` · `content_overlap_all` · [Coh-Metrix](https://doi.org/10.1017/CBO9780511894664)
{ .metric-meta }

<!-- --8<-- [start:calc_overlap] -->
``` {.python .signature}
calc_overlap(sets, adjacent=True)
```

The binary overlap of Coh-Metrix (CRFNO1, CRFAO1, CRFSO1 over the adjacent pairs, CRFNOa, CRFAOa, CRFSOa over all of them): the share of the pairs of sentences that share at least one element; `nan` for a text shorter than two sentences.

$$
\frac{\textrm{Number of pairs sharing an element}}{\textrm{Number of pairs}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sets` | `list[set[str]]` | - | Elements of every sentence |
| `adjacent` | `bool` | `True` | Count the adjacent pairs only, otherwise all the pairs |
<!-- --8<-- [end:calc_overlap] -->

</div>

<div class="metric-card" markdown>

### Proportional overlap { #proportional_overlap }

`content_overlap_prop_adjacent` · `content_overlap_prop_all` · [Coh-Metrix](https://doi.org/10.1017/CBO9780511894664)
{ .metric-meta }

<!-- --8<-- [start:calc_proportional_overlap] -->
``` {.python .signature}
calc_proportional_overlap(sets, adjacent=True)
```

The proportional overlap of Coh-Metrix (CRFCWO1, CRFCWOa): the Dice coefficient of a pair of sentences (`dice`) averaged over the pairs; `nan` for a text shorter than two sentences.

$$
\frac{1}{\textrm{Number of pairs}} \sum_{(A, B)} \textrm{Dice}(A, B)
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sets` | `list[set[str]]` | - | Elements of every sentence |
| `adjacent` | `bool` | `True` | Count the adjacent pairs only, otherwise all the pairs |
<!-- --8<-- [end:calc_proportional_overlap] -->

<!-- --8<-- [start:dice] -->
``` {.python .signature}
dice(first, second)
```

The Dice coefficient of two sets, 0 for two empty sets.

$$
\frac{2 \times |A \cap B|}{|A| + |B|}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `first` | `frozenset[str]` | - | First set |
| `second` | `frozenset[str]` | - | Second set |
<!-- --8<-- [end:dice] -->

</div>

<div class="metric-card" markdown>

### Overlap with the next sentences and paragraphs { #forward_overlap }

`noun_overlap_2_sent` · `argument_overlap_2_sent` · `content_overlap_2_sent` · `noun_overlap_para` · `argument_overlap_para` · `content_overlap_para` · [TAACO](https://doi.org/10.3758/s13428-015-0651-7)
{ .metric-meta }

<!-- --8<-- [start:CohesionStats-forward_overlap] -->
The adjacent overlap of TAACO, by the lemmas of the nouns, of the arguments and of the content words: the share of the distinct lemmas of a sentence repeated in one of the next two sentences (`adjacent_overlap_2_*_sent`), and of a paragraph repeated in the next paragraph (`adjacent_overlap_*_para`), over all the sentences or paragraphs that have them (`calc_forward_overlap`). Unlike the binary overlap, a pair of segments counts by the share of the lemmas they share. A paragraph is a part of the text between blank lines: a sentence whose first word carries `paragraph_start` opens one.
<!-- --8<-- [end:CohesionStats-forward_overlap] -->

<!-- --8<-- [start:calc_forward_overlap] -->
``` {.python .signature}
calc_forward_overlap(sets, span=1)
```

The share of the elements of a segment repeated in the next ones: the distinct elements of every segment with `span` segments after it that one of these segments holds, over the distinct elements of those segments; `nan` for no more segments than `span` or for segments without elements.

$$
\frac{\sum_{i=1}^{n-k} |A_i \cap (A_{i+1} \cup \dots \cup A_{i+k})|}{\sum_{i=1}^{n-k} |A_i|}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sets` | `list[set[str]]` | - | Elements of every segment |
| `span` | `int` | `1` | Number $k$ of the next segments a segment is compared with |

Segments that are a string, a `Doc`, an iterator or a segment that is not a list of strings raise `SourceTypeError`, a span that is not an integer above 0 `ParameterError`.
<!-- --8<-- [end:calc_forward_overlap] -->

=== "Code"

    ``` python
    from anyts.cohesion_stats import calc_forward_overlap

    calc_forward_overlap([{"cat", "mat"}, {"dog"}, {"cat"}], span=2)
    ```

=== "Result"

    ```
    0.5
    ```

</div>

<div class="metric-card" markdown>

### Pronouns and demonstratives { #pronouns }

`p_pronouns` · `pronoun_noun_ratio` · `p_demonstratives`
{ .metric-meta }

<!-- --8<-- [start:CohesionStats-pronouns] -->
The pronouns, the nouns and the demonstratives are the words `analyze` marks so, with the features of `word_info` by default.

$$
\frac{\textrm{Number of pronouns}}{\textrm{Number of words}}, \quad \frac{\textrm{Number of pronouns}}{\textrm{Number of nouns}}, \quad \frac{\textrm{Number of demonstratives}}{\textrm{Number of words}}
$$
<!-- --8<-- [end:CohesionStats-pronouns] -->

</div>

<div class="metric-card" markdown>

### Givenness { #given }

`p_given`
{ .metric-meta }

<!-- --8<-- [start:count_given] -->
``` {.python .signature}
count_given(sents)
```

The number of given elements: an element is given when the same lemma was used earlier in any sentence, the current one included; the first occurrence is new.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[list[str]]` | - | Lemmas of every sentence in the order of the text |
<!-- --8<-- [end:count_given] -->

</div>

<div class="metric-card" markdown>

### Temporal cohesion { #temporal_cohesion }

`tense_repetition` · `mood_repetition` · `aspect_repetition` · `temporal_cohesion` · [Coh-Metrix](https://doi.org/10.1017/CBO9780511894664)
{ .metric-meta }

<!-- --8<-- [start:calc_repetition] -->
``` {.python .signature}
calc_repetition(sents)
```

The repetition of the tense and of the aspect of Coh-Metrix (SMTEMP): the share of the adjacent pairs of sentences whose verbs have the same dominant value of the feature; a pair where one of the sentences has no verb with the feature is skipped, and without a single such pair the value is `nan`.

$$
\frac{\textrm{Number of pairs with the same dominant value}}{\textrm{Number of pairs with the feature}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[list[str]]` | - | Values of the feature of the verbs of every sentence |
<!-- --8<-- [end:calc_repetition] -->

<!-- --8<-- [start:dominant] -->
``` {.python .signature}
dominant(values)
```

The dominant value: the most frequent one, the first of the equally frequent; `None` for an empty list.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `values` | `list[str]` | - | Values |
<!-- --8<-- [end:dominant] -->

</div>

<div class="metric-card" markdown>

### Connectors { #connectors }

`connectors` · `connectors_inter` · `connectors_intra` · `connectors_<class>` · `connectors_<kind>`
{ .metric-meta }

<!-- --8<-- [start:CohesionStats-connectors] -->
The occurrences of the connectors found in every sentence by the matcher of `connector_matcher_class`, per 1000 words. An inter-sentential connector links a sentence to the ones before: it opens a sentence, unless the matcher takes it for a subordinator (`is_subordinator`), whose clause or phrase belongs to the same sentence; the others are intra-sentential. Every class and kind of the matcher gives a density: `connectors_causal`, `connectors_adversative`, `connectors_concessive`, `connectors_temporal`, `connectors_additive`, `connectors_conditional`, `connectors_reformulative`, `connectors_primary` and `connectors_secondary` by default.

$$
1000 \cdot \frac{\textrm{Number of connectors}}{\textrm{Number of words}}
$$
<!-- --8<-- [end:CohesionStats-connectors] -->

</div>

<!-- --8<-- [start:cohesion-checks] -->
A list of sentences that is a string, a `Doc`, an iterator, a set or a table raises `SourceTypeError`, and so does a sentence that is not a list of strings (`check_words`), such as a list of spaCy tokens. The overlaps (`calc_overlap`, `calc_proportional_overlap`, `calc_overlaps`) take a sentence as a set too; `count_given` and `calc_repetition` count the words in order and refuse a set.
<!-- --8<-- [end:cohesion-checks] -->

=== "Code"

    ``` python
    from anyts.cohesion_stats import calc_overlap, calc_repetition, count_given

    sets = [{"cat", "house"}, {"cat", "dog"}, {"bird"}]
    calc_overlap(sets), calc_overlap(sets, adjacent=False)
    count_given([["cat", "house"], ["cat", "dog"], ["house"]])
    calc_repetition([["Pres"], ["Pres", "Past", "Pres"], ["Past"]])
    ```

=== "Result"

    ```
    (0.5, 0.3333333333333333)
    2
    0.5
    ```

## Methods

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

## Overlaps at once { #calc_overlaps }

<!-- --8<-- [start:calc_overlaps] -->
``` {.python .signature}
calc_overlaps(sets, proportional=True)
```

The values of `calc_overlap` and `calc_proportional_overlap` over the adjacent and over all the pairs at once, as an `Overlap` named tuple with the fields `adjacent`, `all`, `prop_adjacent` and `prop_all`; without `proportional` the last two are `nan`. The values over all the pairs come without going through every pair, and none of them depends on the order of the elements in the sets.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sets` | `list[set[str]]` | - | Elements of every sentence |
| `proportional` | `bool` | `True` | Compute the proportional overlap as well |
<!-- --8<-- [end:calc_overlaps] -->

=== "Code"

    ``` python
    from anyts.cohesion_stats import calc_overlaps

    calc_overlaps([{"cat", "house"}, {"cat", "dog"}, {"bird"}])
    ```

=== "Result"

    ```
    Overlap(adjacent=0.5, all=0.3333333333333333, prop_adjacent=0.25, prop_all=0.16666666666666666)
    ```

## Connector matcher { #ConnectorMatcher }

``` {.python .signature}
ConnectorMatcher(connectors)
```

<!-- --8<-- [start:ConnectorMatcher] -->
The search of the connectors (discourse markers: *because*, *however*, *on the other hand*) of a dictionary in the sentences of a text. The dictionary gives the class of every connector - causal, adversative, concessive, temporal, additive, conditional or reformulative (`CONNECTOR_CLASSES`) - and its kind, primary or secondary (`CONNECTOR_KINDS`). A connector is matched by the normalized forms of its words, the longest one at every position, without overlaps; a period or a hyphen inside a connector may be split off by the tokenizer (*e.g.* as `e`, `g`). An occurrence is a `Connector`: the number of the sentence `sent`, the positions `start` and `end` of its words, the connector `text` as the dictionary writes it, its class `cls` and kind `kind`.

Raises:

- `SourceTypeError` - a dictionary that is not a mapping of a phrase to a pair of strings;
- `ParameterError` - an unknown class or kind.
<!-- --8<-- [end:ConnectorMatcher] -->

<!-- --8<-- [start:ConnectorMatcher-find] -->
`find(words, sent_index, pos, breaks, blocked)` returns the occurrences of the connectors in a sentence in the order of its words. The words are those of one sentence without punctuation, the first one its start. With the parts of speech, a one-word connector counts only with one of `pos_tags` or of `pos_extra` for its form, never after one of `not_after_pos`, and with one of `start_only_pos` only at the start of the sentence; a word without a part of speech (`None`) passes. Without the parts of speech the rules that read them are skipped. The positions of the punctuation marks `breaks` cut a connector off its neighbours: a rule does not read a word across a mark, so in *so, the end* the word after the comma neither blocks nor lets the connector count, unless the connector is one of `read_through_marks`, and a mark between the words of a connector of `split_by_marks` makes it none; without them the words are read as adjacent. No connector starts at a word of `blocked`, which a language rules out by more than the words and their parts of speech, such as its parse.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words of the sentence |
| `sent_index` | `int` | `0` | Number of the sentence, written into the occurrences |
| `pos` | `list[str]` | `None` | Parts of speech of the words |
| `breaks` | `set[int]` | `None` | Positions of the words a punctuation mark stands before |
| `blocked` | `set[int]` | `None` | Positions of the words no connector starts at |

Words that are not a list of strings and parts of speech that are not a list of strings and `None` (the tags `token.pos_` of spaCy, not the numbers `token.pos`) and positions that are not a collection raise `SourceTypeError`, a number of the sentence or a position that is not an integer, a position of a mark that is not that of a word after the first, a blocked position that is not that of a word and parts of speech not as many as the words `ParameterError`.
<!-- --8<-- [end:ConnectorMatcher-find] -->

=== "Code"

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
    matcher.find(["The", "before", "and", "after"], pos=["DET", "ADV", "CCONJ", "ADV"])
    ```

=== "Result"

    ```
    [Connector(sent=0, start=0, end=4, text='on the other hand', cls='adversative', kind='secondary')]
    [Connector(sent=0, start=2, end=3, text='and', cls='additive', kind='primary')]
    ```

<!-- --8<-- [start:ConnectorMatcher-is_subordinator] -->
`is_subordinator(connector, pos=None)` checks whether an occurrence of a connector ties its clause or phrase to its own sentence: a connector of `subordinators`, or a one-word connector whose part of speech `pos` is `SCONJ` or `ADP`, but none of `parcellation`. The clause of a subordinating conjunction and the phrase of a preposition belong to the sentence of the connector wherever it stands, so a subordinator opening a sentence (*when he came, ...*, *despite the rain, ...*) does not link it to the ones before. A connector that is not a `Connector` raises `SourceTypeError`.
<!-- --8<-- [end:ConnectorMatcher-is_subordinator] -->

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:CohesionStats-hooks] -->
A language library subclasses `CohesionStats`. By default the words and their features are read from a `Doc` by Universal Dependencies, and there are no connectors:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `analyze(source)` | method | Words of the sentences of a source as `CohesionWord`: the word, its lemma, its part of speech, whether it is a noun, a pronoun, a demonstrative, an argument and a content word, its tense, mood and aspect, whether a punctuation mark stands before it (`break_before`, which the rules of the connectors do not read through) whether no connector starts at it (`connector_blocked`, by a rule of the parse such as an *if* of an indirect question) and whether it opens a paragraph (`paragraph_start`, read on the first word of a sentence); by default those of a `Doc`, sentence by sentence (`doc_units`), with the features of `word_info`; the default marks the sentences after a blank line of the `Doc`; a library that reads a string or a `Doc` without these annotations overrides it |
| `doc_units(doc)` | method | Words of the sentences of a `Doc` as lists of tokens: by its boundaries, or by the extractor over its text (`split_doc_units` of `anyts.utils`) |
| `word_info(unit)` | method | Features of a word of a `Doc`; by default a noun is `NOUN` or `PROPN`, a pronoun `PRON` or a possessive, demonstrative or personal determiner, a demonstrative carries `PronType=Dem`, an argument is `NOUN`, `PROPN` or `PRON`, a content word one of `anyts.constants.CONTENT_UD_POS` and no demonstrative, and the tense, the mood and the aspect are the features `Tense`, `Mood` and `Aspect`; a library sets `connector_blocked` where its parse rules a connector out |
| `load_connectors()` | class method | Dictionary of the connectors of the language, class and kind by connector; empty by default |
| `connector_matcher()` | class method | Matcher of that dictionary, built once for a class and shared by its instances and by searches outside the statistics |
| `connector_matcher_class` | class attribute | Class that finds the connectors with the context rules of the language; `ConnectorMatcher` by default. A matcher with other classes or kinds gives other `connectors_*` attributes, so the subclass sets its own `stats_desc` too |
| `temporal_features` | class attribute | Features of the verbs whose repetitions make the temporal cohesion: a tuple of one or more distinct ones of `tense`, `mood` and `aspect` (`TEMPORAL_FEATURES`), checked when the class is defined; `tense` and `aspect` by default, as in Coh-Metrix |
| `sents_extractor_class`, `join_hyphens` | class attributes | Sentence extractor of a `Doc` without boundaries, joining of the hyphenated words of a `Doc` |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions (`COHESION_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The parameters of a library - its model of a string, its word extractor - go to the constructor of its subclass, which keeps them for its `analyze`. An `analyze` that does not give sentences of `CohesionWord` objects raises `SourceTypeError`.
<!-- --8<-- [end:CohesionStats-hooks] -->

</details>

<details class="library-hooks" markdown>
<summary>Rules of a connector matcher</summary>

<!-- --8<-- [start:ConnectorMatcher-hooks] -->
The rules of a language are class attributes of a subclass, empty by default apart from `pos_tags`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `normalize(text)` | method | Normalized form of a word and of a connector; the lower case by default |
| `blocked_after`, `blocked_before` | class attributes | Words after or before a connector, by its text, that make it no connector (*before the end*) |
| `blocked_after_pos` | class attribute | Parts of speech of the word after a connector, by its text, that make it no connector |
| `not_at_start` | class attribute | Connectors that do not count at the start of a sentence, where they open a reply (*Well, ...*) |
| `only_after` | class attribute | Connectors that count inside a sentence only after these words |
| `read_through_marks` | class attribute | Connectors whose rules read the words before and after them through a punctuation mark: a comma always separates a question word from the verb before it (*asked, why*) |
| `split_by_marks` | class attribute | Connectors of several words that a punctuation mark between their words makes no connector |
| `pos_tags`, `pos_extra` | class attributes | Parts of speech of a one-word connector, `CONNECTOR_POS` of Universal Dependencies by default, and those allowed for a word on top of them |
| `not_after_pos` | class attribute | Parts of speech of the previous word that make a one-word connector no connector (a determiner: *the before and the after*) |
| `start_only_pos` | class attribute | Parts of speech of a one-word connector that counts only at the start of a sentence (a capitalized connector tagged as a proper noun) |
| `subordinators` | class attribute | Connectors that are subordinating conjunctions or prepositions besides the one-word ones tagged `SCONJ` or `ADP` (*as soon as*, *in spite of*), for `is_subordinator` |
| `parcellation` | class attribute | Connectors that are no subordinators whatever their part of speech: a sentence they open is linked to the one before (parcellation), for `is_subordinator` |
| `classes`, `kinds` | class attributes | Classes and kinds of the dictionary; `CONNECTOR_CLASSES` and `CONNECTOR_KINDS` by default. The names `inter` and `intra` (`CONNECTOR_PLACES`) belong to the densities by place of `CohesionStats` and raise `ParameterError` when the class is defined |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The words of the lists and the keys of `pos_extra` are normalized forms; the other lists are keyed by the connector, and a connector of the dictionary finds its rules by its normalized form, however either of them writes it. A rule that is not a collection of strings, or a mapping of strings to them, raises `SourceTypeError` when the class is defined.
<!-- --8<-- [end:ConnectorMatcher-hooks] -->

</details>
