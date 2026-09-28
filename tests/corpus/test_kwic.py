import re
import unicodedata

import pytest
import spacy
from spacy.tokens import Doc

from anyts.corpus import Concordance, format_kwic, kwic, print_kwic
from anyts.exceptions import ParameterError, SourceTypeError

text = (
    "The cat was at the window. The cat was called Tom, and the cats wanted the window. "
    "Because the cat slept."
)
LEMMAS = {"cats": "cat", "wanted": "want", "was": "be", "slept": "sleep"}


def lemmatize(word, tokens):
    return [LEMMAS.get(word.lower(), word)]


def words_of(pattern):
    """A tokenizer of the words matched by a regular expression"""

    def tokenize(text):
        return [(m.start(), m.end(), m.group()) for m in re.finditer(pattern, text)]

    return tokenize


def test_kwic():
    assert kwic(text, "cat", window=2) == [
        Concordance(4, 7, "The", "cat", "was at"),
        Concordance(31, 34, "window. The", "cat", "was called"),
        Concordance(95, 98, "Because the", "cat", "slept"),
    ]


def test_kwic_without_context():
    assert kwic(text, "cat", window=0) == [
        Concordance(4, 7, "", "cat", ""),
        Concordance(31, 34, "", "cat", ""),
        Concordance(95, 98, "", "cat", ""),
    ]


def test_kwic_by_case():
    assert [line.keyword for line in kwic("Cat and cat", "cat")] == ["Cat", "cat"]
    assert [line.keyword for line in kwic("Cat and cat", "cat", ignore_case=False)] == ["cat"]


def test_kwic_by_lemma():
    # Without a lemmatizer a string word is its own lemma
    assert [line.keyword for line in kwic(text, "cat", by_lemma=True)] == ["cat", "cat", "cat"]
    found = kwic(text, "cat", by_lemma=True, lemmatize=lemmatize)
    assert [line.keyword for line in found] == ["cat", "cat", "cats", "cat"]
    assert kwic(text, "cats", by_lemma=True, lemmatize=lemmatize) == found


def test_kwic_of_a_phrase():
    expected = [Concordance(64, 81, "cats", "wanted the window", ". Because")]
    assert kwic(text, "wanted the window", window=1) == expected
    assert kwic(text, "want the window", window=1, by_lemma=True, lemmatize=lemmatize) == expected


def test_kwic_of_an_absent_word():
    assert kwic(text, "dog") == []


def test_kwic_does_not_overlap():
    assert kwic("cat cat cat", "cat cat") == [Concordance(0, 7, "", "cat cat", "cat")]


def test_kwic_collapses_whitespace():
    assert kwic("The cat:\n\n  «sleeps» calmly", "sleeps", window=1) == [
        Concordance(13, 19, "cat: «", "sleeps", "» calmly")
    ]
    assert kwic("cat\n\tsleeps in the bed", "cat sleeps", window=1) == [
        Concordance(0, 11, "", "cat sleeps", "in")
    ]


def test_kwic_of_a_blank_doc():
    assert kwic(spacy.blank("xx")(text), "cat", window=2) == kwic(text, "cat", window=2)


def test_kwic_of_a_doc_with_lemmas():
    words = ["My", "friend", "saw", "a", "saw", "."]
    lemmas = ["my", "friend", "see", "a", "saw", "."]
    doc = Doc(spacy.blank("xx").vocab, words=words, lemmas=lemmas)
    assert [(line.start, line.keyword) for line in kwic(doc, "see", by_lemma=True)] == [
        (10, "saw")
    ]
    # A word is found by its own form too
    assert [line.start for line in kwic(doc, "saw", by_lemma=True)] == [10, 16]
    assert kwic(doc.text, "see", by_lemma=True) == []
    # The lemmatizer gets the tokens of a word of a Doc
    seen = []
    kwic(doc, "saw", by_lemma=True, lemmatize=lambda word, tokens: seen.append(tokens) or [word])
    # the words of the text first, then the keyword
    assert [len(tokens) for tokens in seen] == [1, 1, 1, 1, 1, 0]


def test_kwic_splits_the_keyword_like_the_text():
    assert [line.keyword for line in kwic("He went to the U.S. in May.", "U.S.")] == ["U.S"]
    assert [line.keyword for line in kwic("Paid 20 € for it.", "20 €")] == ["20"]
    assert [
        line.keyword
        for line in kwic("He went to the U.S. in May.", "U.S", tokenize=words_of(r"[\w.]+\w|\w"))
    ] == ["U.S"]


def test_kwic_fold():
    def strip_accents(word):
        decomposed = unicodedata.normalize("NFD", word.lower())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    sample = "A café, a cafe and a CAFÉ."
    assert [line.keyword for line in kwic(sample, "cafe")] == ["cafe"]
    assert [line.keyword for line in kwic(sample, "cafe", fold=strip_accents)] == [
        "café",
        "cafe",
        "CAFÉ",
    ]


def test_kwic_join_hyphens():
    doc = spacy.blank("xx")("A well-known cat and a well known dog.")
    assert kwic(doc, "well-known", tokenize=words_of(r"\w+(?:-\w+)*")) == []
    assert kwic(doc, "well-known", tokenize=words_of(r"\w+(?:-\w+)*"), join_hyphens=True) == [
        Concordance(2, 12, "A", "well-known", "cat and a well known")
    ]
    assert [line.keyword for line in kwic(doc, "well known")] == ["well-known", "well known"]


def test_kwic_of_a_wrong_source():
    with pytest.raises(SourceTypeError, match=r"^The data source is set incorrectly$"):
        kwic(["cat"], "cat")
    with pytest.raises(SourceTypeError, match=r"^The keyword must be a string, not list$"):
        kwic(text, ["cat"])


@pytest.mark.parametrize(("keyword", "window"), [("  ", 5), ("?!", 5), ("cat", -1), ("cat", 2.5)])
def test_kwic_errors(keyword, window):
    with pytest.raises(ParameterError):
        kwic(text, keyword, window=window)


@pytest.mark.parametrize(
    ("hook", "value"), [("tokenize", "x"), ("lemmatize", "x"), ("fold", "x"), ("fold", None)]
)
def test_kwic_hooks_checked(hook, value):
    with pytest.raises(SourceTypeError, match=r"must be callable, not"):
        kwic(text, "cat", ignore_case=False, **{hook: value})


def test_kwic_lemmatizer_of_one_lemma():
    # A lemma given as a string is one lemma, not its letters
    found = kwic(text, "cat", by_lemma=True, lemmatize=lambda word, tokens: LEMMAS.get(word, word))
    assert [line.keyword for line in found] == ["cat", "cat", "cats", "cat"]


def test_format_kwic():
    lines = kwic(text, "cat", window=2, by_lemma=True, lemmatize=lemmatize)
    assert format_kwic(lines, width=10).split("\n") == [
        "       The  cat   was at",
        "indow. The  cat   was called",
        "   and the  cats  wanted the",
        "ecause the  cat   slept",
    ]
    assert format_kwic([]) == ""
    assert format_kwic(kwic("cat\nsleeps", "cat sleeps"), width=1).split("\n") == [
        "   cat sleeps  "
    ]


@pytest.mark.parametrize("width", [0, -1, 2.5])
def test_format_kwic_errors(width):
    with pytest.raises(ParameterError):
        format_kwic(kwic(text, "cat"), width=width)


def test_print_kwic(capsys):
    lines = kwic(text, "cat", window=2)
    print_kwic(lines, width=10)
    assert capsys.readouterr().out == format_kwic(lines, width=10) + "\n"


def test_kwic_byte_order_mark():
    sample = "\ufeffCat and cat."
    assert len(kwic(sample, "cat")) == len(kwic(spacy.blank("xx")(sample), "cat")) == 2
    assert kwic(spacy.blank("xx")(sample), "cat")[0].start == 1


def test_kwic_join_hyphens_with_the_default_tokenizer():
    sample = "Кто-то пришёл, и кто-то ушёл."
    for source in (sample, spacy.blank("ru")(sample)):
        found = kwic(source, "кто-то", join_hyphens=True)
        assert [line.keyword for line in found] == ["Кто-то", "кто-то"]
        assert kwic(source, "то", join_hyphens=True) == []
    assert len(kwic(sample, "то")) == 2


def test_kwic_composed_forms():
    decomposed = unicodedata.normalize("NFD", "El café está aquí.")
    assert [line.keyword for line in kwic(decomposed, "café")] == [decomposed[3:8]]
    assert len(kwic(decomposed, "café", ignore_case=False)) == 1
    doc = spacy.blank("xx")("Die Ge­schichte ist lang.")
    assert [line.keyword for line in kwic(doc, "Geschichte", ignore_case=False)] == ["Ge­schichte"]
    lemmas = kwic(doc, "geschichte", by_lemma=True, lemmatize=lambda word, tokens: word)
    assert len(lemmas) == 1


def test_kwic_phrase_stops_at_the_end_of_a_sentence():
    text = "He saw the window.\n\nThe cat sat. A dog! Cat food and dog cat."
    assert kwic(text, "window the cat") == []
    assert [line.keyword for line in kwic(text, "window. The cat")] == ["window. The cat"]
    assert [line.keyword for line in kwic(text, "dog cat")] == ["dog cat"]
    assert kwic("A line\n\nanother line", "line another") == []
    assert len(kwic("A line\nanother line", "line another")) == 1
    assert [line.keyword for line in kwic("The U.S. Army came.", "U.S. Army")] == ["U.S. Army"]
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    assert kwic(nlp("A dog. Cat here and dog cat."), "dog cat")[0].start == 20
    assert kwic(spacy.blank("xx")("A dog. Cat here."), "dog cat") == []


def test_format_kwic_iterables_and_composed_forms():
    lines = kwic(text, "cat", window=2)
    assert format_kwic(line for line in lines) == format_kwic(lines)
    decomposed = unicodedata.normalize("NFD", "El niño come. El perro come.")
    formatted = format_kwic(kwic(decomposed, "come", window=1), width=6).split("\n")
    assert formatted == ["  niño  come  . El", " perro  come  "]
    assert [line.index("come") for line in formatted] == [8, 8]
