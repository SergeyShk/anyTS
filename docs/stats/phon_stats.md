# Phonetic statistics

!!! info ""
    **anyts.phon_stats.PhonStats**

## Description

<!-- --8<-- [start:PhonStats] -->
The phonetic statistics of a text: the shares of the vowels, the sonorants and the voiced and voiceless obstruents, the ratio of the consonants to the vowels, the consonant clusters, the hiatuses, the entropy of the CV patterns of the words, the hardness, the alliteration and the assonance, the open syllables and the mean length of a syllable. A sound is a letter of a word by default, or a sound of its transcription when a library gives one. The data source can be a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy); the words are taken in lower case, and an extractor passed explicitly is used on the text of a `Doc`.

A source that is neither a string nor a `Doc` and an extractor of another type raise `SourceTypeError`, a source without words `SourceError`, a window that is not an integer of at least 2 `ParameterError`.
<!-- --8<-- [end:PhonStats] -->

## Language hooks

<!-- --8<-- [start:PhonStats-hooks] -->
A language library subclasses `PhonStats`:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `vowels`, `sonorants`, `voiced`, `voiceless` | class attributes | Classes of the sounds - the vowels, the sonorants and the voiced and voiceless obstruents; the consonants are the last three, and the classes and `skipped` must not overlap, checked when the class is defined |
| `skipped` | class attribute | Sounds that neither count nor break a consonant cluster, such as a sign that marks the consonant before it |
| `glides` | class attribute | Vowels that make no hiatus after a vowel, such as a letter that writes a glide and a vowel |
| `transcribe(word)` | method | Sounds of a word; its letters by default |
| `syllabify(word)` | method | Syllables of a word as it writes them; an abstract method, since syllables depend on the language |
| `syllable_sounds(word)` | method | Sounds of every syllable of a word; the transcription of every syllable of `syllabify` by default |
| `word_hiatus(word)` | method | Number of the hiatuses of a word; its runs of vowels by `count_hiatus` with `glides` by default, otherwise for instance the vowels at the boundaries of its syllables |
| `doc_words(doc)` | method | Words of a `Doc`; those of `iter_doc_words` in lower case by default |
| `words_extractor_class`, `join_hyphens` | class attributes | Word extractor of a string, joining of the hyphenated words of a `Doc` |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions, headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
<!-- --8<-- [end:PhonStats-hooks] -->

## Parameters

<!-- --8<-- [start:PhonStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source |
| `words_extractor` | WordsExtractor | `None` | Word extraction tool; used for a `Doc` too, on its text |
| `window_len` | int | `3` | Window in words of the alliteration and the assonance |
<!-- --8<-- [end:PhonStats-parameters] -->

## Attributes

<!-- --8<-- [start:PhonStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `words` | tuple[str] | Words in lower case |
| `window_len` | int | Window of the alliteration and the assonance |
| `syllables`, `sounds` | tuple | Syllables (`syllabify`) and sounds (`transcribe`) of every word |
| `n_vowels`, `n_sonorants`, `n_voiced`, `n_voiceless`, `n_consonants` | int | Numbers of the sounds by class |
| `c_clusters` | dict[int, int] | Number of the consonant clusters by length (`consonant_clusters`) |
| `c_syllable_patterns` | dict[str, int] | Number of the syllables by CV pattern; a syllable without a sound of the classes (a number) is no syllable |
| `p_vowels`, `p_sonorants`, `p_voiced`, `p_voiceless` | float | Shares of the sounds by class |
| `consonant_vowel_ratio` | float | Ratio of the consonants to the vowels |
| `p_heavy_clusters` | float | Share of the clusters of three consonants or more |
| `p_hiatus` | float | Hiatuses per word |
| `cv_entropy` | float | Shannon entropy of the CV patterns of the words, in bits |
| `hardness` | float | Voiceless consonants to the vowels and the sonorants |
| `alliteration`, `assonance` | float | Repetition index of the consonants and of the vowels (`calc_repetition_index`) |
| `p_open_syllables` | float | Share of the syllables that end in a vowel |
| `mean_syllable_len` | float | Mean length of a syllable in sounds |

A share or a ratio without sounds, clusters or syllables to divide by is `nan`, and so are the hiatuses per word and the entropy of a text without sounds.
<!-- --8<-- [end:PhonStats-attributes] -->

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

## Metric functions

The metrics and their functions are described in the [metric functions](phon_stats_funcs.md) section.

## Usage example

!!! example "Example"

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
    stats.c_clusters, stats.p_hiatus
    # ({1: 7, 2: 4, 3: 1}, 0.2222222222222222)
    ```
