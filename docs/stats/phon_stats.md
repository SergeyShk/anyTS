# Phonetic statistics

``` {.python .signature}
PhonStats(source, words_extractor=None, window_len=3)
```

<!-- --8<-- [start:PhonStats] -->
The phonetic statistics of a text: its sounds by class, their clusters, sequences and repetitions, and its syllables. A sound is a letter of a word by default, or a sound of its transcription when a library gives one. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy); the words are taken in lower case, and an extractor passed explicitly is used on the text of a `Doc`.

Raises:

- `SourceTypeError` - a source that is neither a string nor a `Doc`, an extractor of another type;
- `SourceError` - a source without words;
- `ParameterError` - a window that is not an integer of at least 2.
<!-- --8<-- [end:PhonStats] -->

=== "Code"

    ``` python
    import re

    from anyts.phon_stats import PhonStats


    class Phon(PhonStats):
        vowels = frozenset("aeiou")
        sonorants = frozenset("lmnrwy")
        voiced = frozenset("bdgvz")
        voiceless = frozenset("cfhkpqstx")

        def syllabify(self, word):
            return re.findall(r"[^aeiou]*[aeiou]+(?:[^aeiou]+$)?", word) or [word]


    stats = Phon("The poet sat on a stone by the stream")
    stats.print_stats()
    ```

=== "Result"

    ```
                     Statistic                 |  Value
    ------------------------------------------------------
    Share of vowels                            |   0.38
    Share of sonorant consonants               |   0.17
    Share of voiced obstruents                 |   0.03
    Share of voiceless obstruents              |   0.41
    Ratio of consonants to vowels              |   1.64
    Share of clusters of 3 consonants or more  |   0.08
    Hiatuses per word                          |   0.22
    Entropy of the CV patterns of words (bits) |   2.95
    Hardness                                   |   0.75
    Alliteration index                         |   0.61
    Assonance index                            |   0.82
    Share of open syllables                    |   0.50
    Mean length of a syllable (sounds)         |   2.90
    ```

## Parameters

<!-- --8<-- [start:PhonStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source |
| `words_extractor` | `WordsExtractor` | `None` | Word extraction tool; used for a `Doc` too, on its text |
| `window_len` | `int` | `3` | Window in words of the alliteration and the assonance (`PHON_WINDOW_LEN`) |
<!-- --8<-- [end:PhonStats-parameters] -->

## Attributes

<!-- --8<-- [start:PhonStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `words` | `tuple[str]` | Words in lower case |
| `window_len` | `int` | Window of the alliteration and the assonance |
| `syllables`, `sounds` | `tuple` | Syllables (`syllabify`) and sounds (`transcribe`) of every word |
| `n_vowels`, `n_sonorants`, `n_voiced`, `n_voiceless`, `n_consonants` | `int` | Numbers of the sounds by class |
| `c_clusters` | `dict[int, int]` | Number of the consonant clusters by length (`consonant_clusters`) |
| `c_syllable_patterns` | `dict[str, int]` | Number of the syllables by CV pattern |
<!-- --8<-- [end:PhonStats-attributes] -->

## Metrics

<!-- --8<-- [start:PhonStats-metrics] -->
Every metric is an attribute of the object, computed when it is created, and `get_stats` gives them all.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`p_vowels`](#sound_shares) | Share of the vowels among the sounds of the classes | 0-1, `nan` without sounds | A more vocalic text |
| [`p_sonorants`](#sound_shares) | Share of the sonorants among the sounds of the classes | 0-1, `nan` without sounds | A more sonorous text |
| [`p_voiced`](#sound_shares) | Share of the voiced obstruents among the sounds of the classes | 0-1, `nan` without sounds | More voiced obstruents |
| [`p_voiceless`](#sound_shares) | Share of the voiceless obstruents among the sounds of the classes | 0-1, `nan` without sounds | More voiceless obstruents |
| [`consonant_vowel_ratio`](#consonant_vowel_ratio) | Ratio of the consonants to the vowels | 0 and above, `nan` without vowels | Denser consonants |
| [`p_heavy_clusters`](#consonant_clusters) | Share of the clusters of three consonants or more | 0-1, `nan` without clusters | Heavier clusters |
| [`p_hiatus`](#hiatus) | Hiatuses of `word_hiatus` per word | 0 and above, `nan` without sounds | More vowels in a row |
| [`cv_entropy`](#cv_entropy) | Shannon entropy of the CV patterns of the words, in bits | 0 and above, `nan` without sounds | More varied shapes of the words |
| [`hardness`](#hardness) | Voiceless obstruents to the vowels and the sonorants | 0 and above, `nan` without vowels and sonorants | A harder sound |
| [`alliteration`](#repetition_index) | Repetition index of the consonants in windows of `window_len` words | 0 and above, `nan` for a text shorter than the window or with no consonant shared by two words | Consonants repeated closer together |
| [`assonance`](#repetition_index) | Repetition index of the vowels in windows of `window_len` words | 0 and above, `nan` for a text shorter than the window or with no vowel shared by two words | Vowels repeated closer together |
| [`p_open_syllables`](#syllables) | Share of the syllables that end in a vowel | 0-1, `nan` without syllables | More open syllables |
| [`mean_syllable_len`](#syllables) | Mean length of a syllable in sounds | 1 and above, `nan` without syllables | Longer syllables |
<!-- --8<-- [end:PhonStats-metrics] -->

<div class="metric-card" markdown>

### Shares of the classes of the sounds { #sound_shares }

`p_vowels` · `p_sonorants` · `p_voiced` · `p_voiceless`
{ .metric-meta }

<!-- --8<-- [start:PhonStats-sound_shares] -->
The share of the sounds of every class - the vowels, the sonorants and the voiced and voiceless obstruents - among the sounds of all of them; a sound of `skipped` or of no class (a digit, a letter of another script) counts in none.

$$
\frac{\textrm{Number of sounds of the class}}{\textrm{Number of vowels and consonants}}
$$
<!-- --8<-- [end:PhonStats-sound_shares] -->

</div>

<div class="metric-card" markdown>

### Ratio of the consonants to the vowels { #consonant_vowel_ratio }

`consonant_vowel_ratio`
{ .metric-meta }

<!-- --8<-- [start:PhonStats-consonant_vowel_ratio] -->
The number of the consonants `n_consonants` to the number of the vowels `n_vowels`.

$$
\frac{\textrm{Number of consonants}}{\textrm{Number of vowels}}
$$
<!-- --8<-- [end:PhonStats-consonant_vowel_ratio] -->

</div>

<div class="metric-card" markdown>

### Consonant clusters { #consonant_clusters }

`p_heavy_clusters` · `c_clusters`
{ .metric-meta }

<!-- --8<-- [start:consonant_clusters] -->
``` {.python .signature}
consonant_clusters(sounds, consonants, skipped=())
```

The lengths of the consonant clusters of a word in order: a cluster is a run of consonants, a single one included; a sound of `skipped` neither counts nor breaks the run, any other sound breaks it.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sounds` | `list[str]` | - | Sounds or letters of the word |
| `consonants` | `Collection[str]` | - | Consonants |
| `skipped` | `Collection[str]` | `()` | Sounds that keep a cluster whole, such as a sign that marks the consonant before it |
<!-- --8<-- [end:consonant_clusters] -->

</div>

<div class="metric-card" markdown>

### Hiatuses { #hiatus }

`p_hiatus`
{ .metric-meta }

<!-- --8<-- [start:count_hiatus] -->
``` {.python .signature}
count_hiatus(sounds, vowels, glides=())
```

The number of the hiatuses of a word by its vowels in a row: a run of two vowels or more is one hiatus; a vowel of `glides` after a vowel makes none.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sounds` | `list[str]` | - | Sounds or letters of the word |
| `vowels` | `Collection[str]` | - | Vowels |
| `glides` | `Collection[str]` | `()` | Vowels that make no hiatus after a vowel, such as a letter that writes a glide and a vowel |
<!-- --8<-- [end:count_hiatus] -->

</div>

<div class="metric-card" markdown>

### Entropy of the CV patterns { #cv_entropy }

`cv_entropy`
{ .metric-meta }

<!-- --8<-- [start:PhonStats-cv_entropy] -->
The Shannon entropy of the CV patterns of the words (`cv_pattern`), in bits, where $P(p)$ is the share of the words with the pattern $p$ among the words that have one.

$$
-\sum_{p} P(p) \log_2 P(p)
$$
<!-- --8<-- [end:PhonStats-cv_entropy] -->

<!-- --8<-- [start:cv_pattern] -->
``` {.python .signature}
cv_pattern(sounds, vowels, consonants)
```

The CV pattern of a word or a syllable: V for a vowel, C for a consonant, the other sounds (signs, digits, letters of another script) left out.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sounds` | `list[str]` | - | Sounds or letters of the word |
| `vowels` | `Collection[str]` | - | Vowels |
| `consonants` | `Collection[str]` | - | Consonants |
<!-- --8<-- [end:cv_pattern] -->

</div>

<div class="metric-card" markdown>

### Hardness { #hardness }

`hardness`
{ .metric-meta }

<!-- --8<-- [start:PhonStats-hardness] -->
The number of the voiceless obstruents to the number of the vowels and the sonorants.

$$
\frac{\textrm{Number of voiceless obstruents}}{\textrm{Number of vowels} + \textrm{Number of sonorants}}
$$
<!-- --8<-- [end:PhonStats-hardness] -->

</div>

<div class="metric-card" markdown>

### Alliteration and assonance { #repetition_index }

`alliteration` · `assonance`
{ .metric-meta }

<!-- --8<-- [start:calc_repetition_index] -->
``` {.python .signature}
calc_repetition_index(words, window_len, features=None)
```

The repetition index: the number of windows of `window_len` neighbouring words where a feature (a letter or a sound) occurs in two words or more, summed over the features, divided by the number expected if the words stood in random order. A window of shuffled words is a sample without replacement, so for a feature found in \(K\) of the \(N\) words, a window of \(w\) words holds it in two words or more with the hypergeometric probability

$$
P = 1 - \frac{\binom{N-K}{w} + K \binom{N-K}{w-1}}{\binom{N}{w}}
$$

and the expected number is the sum of these probabilities over the features times the \(N - w + 1\) windows. Since the expectation comes from the text itself, the index shows whether the repetitions gather in neighbouring words, not how frequent a feature is: it averages to 1 over the orders of the words and is well above 1 when the repetitions come closer than chance. A word counts a feature once; the index is `nan` for a text shorter than the window or with no feature shared by two words.
<!-- --8<-- [end:calc_repetition_index] -->

<!-- --8<-- [start:calc_repetition_index-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` / `list[list[str]]` | - | Features of every word: a string of its letters or a collection of its sounds |
| `window_len` | `int` | - | Window in words, at least 2 |
| `features` | `Collection[str]` | `None` | Features to count, all of them by default |

Words that are not a list of strings or of collections of strings and features that are not a collection of strings raise `SourceTypeError`, and a `window_len` that is not an integer of at least 2 `ParameterError`.
<!-- --8<-- [end:calc_repetition_index-parameters] -->

</div>

<div class="metric-card" markdown>

### Syllables { #syllables }

`p_open_syllables` · `mean_syllable_len`
{ .metric-meta }

<!-- --8<-- [start:PhonStats-syllables] -->
The syllables are the sounds of every syllable of a word by `syllable_sounds`; a syllable without a sound of the classes (a number) is no syllable, in `c_syllable_patterns` too. An open syllable ends in a vowel by its CV pattern (`cv_pattern`), and the length of a syllable is the length of that pattern: the sounds of the classes, without `skipped` and the signs out of them.
<!-- --8<-- [end:PhonStats-syllables] -->

</div>

The functions know no language: a word is given as its letters (the characters of a string) or the sounds of its transcription, and the classes of the sounds or the features to count come through the parameters.

=== "Code"

    ``` python
    from anyts.phon_stats import calc_repetition_index, consonant_clusters, count_hiatus, cv_pattern

    vowels, consonants = set("aeiou"), set("bcdfghjklmnpqrstvwxyz")
    cv_pattern("strong", vowels, consonants)
    consonant_clusters("strength", consonants)
    count_hiatus("cooperation", vowels)
    calc_repetition_index(["sea", "sun", "gas", "fog", "box", "hat"], 2, {"s"})
    ```

=== "Result"

    ```
    'CCCVCC'
    (3, 4)
    2
    2.0
    ```

## Methods

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:PhonStats-hooks] -->
A language library subclasses `PhonStats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `vowels`, `sonorants`, `voiced`, `voiceless` | class attributes | Classes of the sounds - the vowels, the sonorants and the voiced and voiceless obstruents; the last three are the consonants. The classes and `skipped` must not overlap, checked when the class is defined |
| `skipped` | class attribute | Sounds that neither count nor break a consonant cluster, such as a sign that marks the consonant before it |
| `glides` | class attribute | Vowels that make no hiatus after a vowel, such as a letter that writes a glide and a vowel |
| `transcribe(word)` | method | Sounds of a word; its letters by default |
| `syllabify(word)` | method | Syllables of a word as it writes them; an abstract method |
| `syllable_sounds(word)` | method | Sounds of every syllable of a word; the transcription of every syllable of `syllabify` by default |
| `word_hiatus(word)` | method | Number of the hiatuses of a word; its runs of vowels by `count_hiatus` with `glides` by default, or for instance the vowels at the boundaries of its syllables |
| `doc_words(doc)` | method | Words of a `Doc`; those of `iter_doc_words` in lower case by default |
| `words_extractor_class`, `join_hyphens` | class attributes | Word extractor of a string, joining of the hyphenated words of a `Doc` |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions (`anyts.constants.PHON_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

Classes of sounds that are not collections of strings raise `SourceTypeError` when the class is defined, and a `syllabify` or a `transcribe` that does not return strings raises it when the statistics are computed.
<!-- --8<-- [end:PhonStats-hooks] -->

<!-- --8<-- [start:PhonStats-check_params] -->
``` {.python .signature}
check_params(window_len, *, messages=MESSAGES)
```

Checks the window of the alliteration and the assonance: one that is not an integer of at least 2 raises `ParameterError`.
<!-- --8<-- [end:PhonStats-check_params] -->

</details>
