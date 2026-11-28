import re
import unicodedata

import anyseg
import pytest
from anyseg import Document

from anyts.corpus import Concordance, format_kwic, kwic, print_kwic
from anyts.document import to_document
from anyts.exceptions import ParameterError, SourceTypeError
from tests.documents import parsed

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


def test_kwic_of_a_document_with_lemmas():
    words = ["My", "friend", "saw", "a", "saw", "."]
    lemmas = ["my", "friend", "see", "a", "saw", "."]
    document = parsed(words, lemmas=lemmas)
    assert [(line.start, line.keyword) for line in kwic(document, "see", by_lemma=True)] == [
        (10, "saw")
    ]
    # A word is found by its own form too
    assert [line.start for line in kwic(document, "saw", by_lemma=True)] == [10, 16]
    assert kwic(document.text, "see", by_lemma=True) == []
    # The lemmatizer gets the words of Universal Dependencies of a token, none for the keyword
    seen = []
    kwic(
        document, "saw", by_lemma=True, lemmatize=lambda word, words: seen.append(words) or [word]
    )
    # the words of the text first, then the keyword
    assert [[word.lemma for word in words] for words in seen] == [
        ["my"],
        ["friend"],
        ["see"],
        ["a"],
        ["saw"],
        [],
    ]


def test_kwic_of_a_multiword_token():
    """A multiword token is one word with its words of Universal Dependencies"""
    document = Document.from_tokens(
        "Vino del pueblo", [0, 5, 9], [4, 8, 15], words={1: ["de", "el"]}
    )
    document.set_columns(lemma=["venir", "de", "el", "pueblo"])
    assert [line.keyword for line in kwic(document, "del pueblo")] == ["del pueblo"]
    # Its lemmas are those of a lemmatizer: by default the word alone
    assert kwic(document, "el", by_lemma=True) == []
    found = kwic(
        document,
        "el",
        by_lemma=True,
        lemmatize=lambda word, words: [word, *(w.lemma for w in words)],
    )
    assert [line.keyword for line in found] == ["del"]


def test_kwic_splits_the_keyword_like_the_text():
    assert [line.keyword for line in kwic("He went to the U.S. in May.", "U.S.")] == ["U.S"]
    assert [line.keyword for line in kwic("Paid 20 € for it.", "20 €")] == ["20"]
    assert [
        line.keyword
        for line in kwic("He went to the U.S. in May.", "U.S", tokenize=words_of(r"[\w.]+\w|\w"))
    ] == ["U.S"]


def test_kwic_of_an_abbreviation():
    # A tokenizer by UD leaves the period of an abbreviation to it inside a sentence and splits it
    # off at the end, in the keyword and in the text alike
    def tokenize(text):
        return [
            (token.start, token.end, token.text)
            for token in anyseg.segment(text, lang="es").tokens
        ]

    def sentenize(text):
        sentences = anyseg.segment(text, lang="es").sentences
        return [(sent.start, sent.end, text[sent.start : sent.end]) for sent in sentences]

    def found(source, keyword, by_lemma=False):
        return [
            line.keyword
            for line in kwic(
                source, keyword, by_lemma=by_lemma, tokenize=tokenize, sentenize=sentenize
            )
        ]

    assert found("El Sr. García vino.", "Sr.") == ["Sr."]
    assert found("Vino el Sr.", "Sr.") == ["Sr"]
    assert found("El Sr. García vino.", "el Sr. García") == ["El Sr. García"]
    assert found("Viajó a EE. UU. en mayo.", "EE. UU.") == ["EE. UU."]
    assert found("Viajó a EE. UU.", "EE. UU.") == ["EE. UU"]
    # The lemmas of a word are its form by default, compared without the period too
    assert found("El Sr. García vino.", "Sr.", by_lemma=True) == ["Sr."]


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


def test_kwic_hyphenated_words():
    """A hyphenated word is one word where the tokens of the document keep it whole"""
    text = "A well-known cat and a well known dog."
    document = to_document(text)
    assert [line.keyword for line in kwic(document, "well known")] == ["well-known", "well known"]
    assert kwic(document, "well-known", tokenize=words_of(r"\w+(?:-\w+)*")) == []
    assert kwic(text, "well-known", tokenize=words_of(r"\w+(?:-\w+)*")) == [
        Concordance(2, 12, "A", "well-known", "cat and a well known")
    ]


def test_kwic_of_a_wrong_source():
    with pytest.raises(SourceTypeError, match=r"^The data source cannot be of type list$"):
        kwic(["cat"], "cat")
    with pytest.raises(SourceTypeError, match=r"^The keyword must be a string, not list$"):
        kwic(text, ["cat"])


@pytest.mark.parametrize(("keyword", "window"), [("  ", 5), ("?!", 5), ("cat", -1), ("cat", 2.5)])
def test_kwic_errors(keyword, window):
    with pytest.raises(ParameterError):
        kwic(text, keyword, window=window)


@pytest.mark.parametrize("switch", ["by_lemma", "ignore_case"])
def test_kwic_switches_are_bools(switch):
    with pytest.raises(ParameterError, match=r"must be a bool, not str$"):
        kwic(text, "cat", **{switch: "yes"})


@pytest.mark.parametrize(
    ("hook", "value"),
    [("tokenize", "x"), ("lemmatize", "x"), ("sentenize", "x"), ("fold", "x"), ("fold", None)],
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
    # A text in place of the concordances: the error names them, not the width
    with pytest.raises(
        SourceTypeError, match=r"^An iterable of concordances is expected, not str$"
    ):
        print_kwic(text, "cat")
    with pytest.raises(
        SourceTypeError, match=r"^An iterable of concordances is expected, not Token$"
    ):
        print_kwic(to_document(text).tokens, "cat")


def test_kwic_byte_order_mark():
    sample = "\ufeffCat and cat."
    assert len(kwic(sample, "cat")) == 2
    assert kwic(sample, "cat")[0].start == 1


def test_kwic_hyphenated_words_of_a_tokenizer():
    sample = "Кто-то пришёл, и кто-то ушёл."
    hyphenated = words_of(r"\w+(?:-\w+)*")
    found = kwic(sample, "кто-то", tokenize=hyphenated)
    assert [line.keyword for line in found] == ["Кто-то", "кто-то"]
    assert kwic(sample, "то", tokenize=hyphenated) == []
    assert len(kwic(sample, "то")) == 2


def test_kwic_composed_forms():
    decomposed = unicodedata.normalize("NFD", "El café está aquí.")
    assert [line.keyword for line in kwic(decomposed, "café")] == [decomposed[3:8]]
    assert len(kwic(decomposed, "café", ignore_case=False)) == 1
    hyphenated = "Die Ge­schichte ist lang."
    found = kwic(hyphenated, "Geschichte", ignore_case=False)
    assert [line.keyword for line in found] == ["Ge­schichte"]
    lemmas = kwic(hyphenated, "geschichte", by_lemma=True, lemmatize=lambda word, tokens: word)
    assert len(lemmas) == 1


def test_kwic_phrase_stops_at_the_end_of_a_sentence():
    text = "He saw the window.\n\nThe cat sat. A dog! Cat food and dog cat."
    assert kwic(text, "window the cat") == []
    assert [line.keyword for line in kwic(text, "window. The cat")] == ["window. The cat"]
    assert [line.keyword for line in kwic(text, "dog cat")] == ["dog cat"]
    assert kwic("A line\n\nanother line", "line another") == []
    assert len(kwic("A line\nanother line", "line another")) == 1
    assert [line.keyword for line in kwic("The U.S. Army came.", "U.S. Army")] == ["U.S. Army"]


def test_format_kwic_iterables_and_composed_forms():
    lines = kwic(text, "cat", window=2)
    assert format_kwic(line for line in lines) == format_kwic(lines)
    decomposed = unicodedata.normalize("NFD", "El niño come. El perro come.")
    formatted = format_kwic(kwic(decomposed, "come", window=1), width=6).split("\n")
    assert formatted == ["  niño  come  . El", " perro  come  "]
    assert [line.index("come") for line in formatted] == [8, 8]


def test_kwic_phrase_stops_at_a_sentence_start_on_a_mark():
    # The parser starts the sentence at the opening mark before the word
    words = ["Vino", "ayer", ".", "¿", "Qué", "tal", "?"]
    document = parsed(
        words,
        spaces=[True, False, True, False, True, False, False],
        sent_starts=[True, False, False, True, False, False, False],
    )
    assert kwic(document, "ayer qué") == []
    assert len(kwic(document, "qué tal")) == 1

    # A paragraph ends a phrase in a document with its sentences too
    def one_sentence(gap):
        """A sentence over two lines with the gap between them"""
        return parsed(
            ["Dijo", "uno", gap, "El", "otro", "vino", "."],
            spaces=[True, False, False, True, True, False, False],
            sent_starts=[True, False, False, False, False, False, False],
        )

    assert kwic(one_sentence("\n\n"), "uno el") == []
    assert len(kwic(one_sentence("\n"), "uno el")) == 1


SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def sentences(text):
    """Sentences that end at a final mark only before an upper-case letter"""
    start = 0
    for match in SENT_END.finditer(text):
        yield start, match.start(), text[start : match.start()]
        start = match.end()
    yield start, len(text), text[start:]


def test_kwic_sentenize():
    text = "He was honest... think of the girls. Then oh! he left."
    assert kwic(text, "honest think") == kwic(text, "oh he") == []
    found = kwic(text, "honest think", sentenize=sentences)
    assert [(line.start, line.keyword) for line in found] == [(7, "honest... think")]
    assert [line.keyword for line in kwic(text, "oh he", sentenize=sentences)] == ["oh! he"]
    assert kwic(text, "girls then", sentenize=sentences) == []
    assert len(kwic(text, "girls. Then", sentenize=sentences)) == 1
    # The sentences of a document come first
    document = to_document(text)
    assert kwic(document, "oh he", sentenize=sentences) == []
    # A final mark in the keyword lets a phrase cross whatever its case, in a document too
    assert len(kwic(text, "girls. then", sentenize=sentences)) == 1
    assert len(kwic(document, "girls. then", sentenize=sentences)) == 1
    # The sentences may come in any order
    backwards = lambda text: reversed(list(sentences(text)))  # noqa: E731
    assert kwic(text, "honest think", sentenize=backwards) == found
    assert kwic(text, "girls then", sentenize=backwards) == []
    # A sentence of a string may start on the opening mark before a word
    dialogue = "He waited\n—Then go, she said."
    assert len(kwic(dialogue, "waited then")) == 1
    by_lines = lambda text: [(0, 9, text[:9]), (10, len(text), text[10:])]  # noqa: E731
    assert kwic(dialogue, "waited then", sentenize=by_lines) == []
    # A sentence ends after a run of closing marks too
    assert kwic('He said "stop.") Then he left.', "stop then") == []
    # A paragraph ends a phrase whatever the sentences
    one = lambda text: [(0, len(text), text)]  # noqa: E731
    assert kwic("A line\n\nanother line", "line another", sentenize=one) == []
    assert len(kwic("A line\nanother line", "line another", sentenize=one)) == 1


@pytest.mark.parametrize("concordances", [None, "cat"])
def test_format_kwic_of_no_concordances(concordances):
    with pytest.raises(SourceTypeError, match=r"^An iterable of concordances is expected, not "):
        format_kwic(concordances)


def test_kwic_checks_the_words_of_its_tokenizer():
    with pytest.raises(SourceTypeError, match=r"^The tokenize must give triples"):
        kwic("The cat sleeps", "cat", tokenize=str.split)


def test_kwic_checks_the_sentences_of_its_splitter():
    with pytest.raises(SourceTypeError, match=r"^The sentenize must give triples"):
        kwic("The cat. It sleeps.", "cat it", sentenize=lambda text: [(0, 99, text)])
