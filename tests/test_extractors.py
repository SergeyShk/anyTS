import gc
import re
import subprocess
import sys
import unicodedata
import weakref

import pytest
import spacy

from anyts import CharNgramsExtractor, SentsExtractor, WordsExtractor
from anyts.exceptions import ParameterError, SourceTypeError
from anyts.extractors import NUMBER_PATTERN, Extractor, _word_pattern

TEXT = (
    "Thesauri are a special class of lexicographic resources marked by the following"
    " features: the completeness of the meanings of the vocabulary of a language or of its"
    " segments; the thematic, or ideographic, ordering of the meanings of the words. The"
    " difference between thesauri and formal ontologies lies in the turn to the sphere of"
    " lexical meanings, in the relations not only between the meanings and the words that"
    " express them, but also between the meanings themselves (the record of various semantic"
    " relations inside the dictionary)."
)


def test_extractor_is_abstract():
    with pytest.raises(TypeError):
        Extractor()  # type: ignore[abstract]


@pytest.mark.parametrize(
    "mark", ["\u0301", "\u0903", "\u20dd", "\U000e0100", "\u00ad", "\u200c", "\u200d"]
)
def test_word_pattern_continues_with_marks_and_joiners(mark):
    assert _word_pattern().fullmatch(f"a{mark}b")
    assert _word_pattern().findall(f"{mark}ab") == ["ab"]


@pytest.mark.parametrize("char", ["\u200b", "\ufeff", "-", "'", " "])
def test_word_pattern_breaks_at_other_characters(char):
    assert _word_pattern().findall(f"a{char}b") == ["a", "b"]


def test_word_pattern_built_on_first_use():
    code = (
        "from anyts import extractors; "
        "print(extractors._word_pattern.cache_info().currsize); "
        "extractors.WordsExtractor().extract('cat'); "
        "print(extractors._word_pattern.cache_info().currsize)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.split() == ["0", "1"]


@pytest.mark.parametrize(
    "extractor",
    [
        SentsExtractor,
        WordsExtractor,
        CharNgramsExtractor,
        lambda: CharNgramsExtractor(within_words=True),
    ],
)
def test_extractor_freed_without_gc(extractor):
    gc.disable()
    try:
        instance = extractor()
        instance.extract(TEXT)
        ref = weakref.ref(instance)
        del instance
        assert ref() is None
    finally:
        gc.enable()


class TestSentsExtractor:
    def test_extract(self):
        se = SentsExtractor()
        assert se.extract(TEXT) == se.sents
        assert len(se.sents) == 2
        assert se.sents[0].startswith("Thesauri are")
        assert se.sents[1].startswith("The difference")
        assert se.tokenizer is None

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "It rains. Does it? Yes! Well… Go.",
                ("It rains.", "Does it?", "Yes!", "Well…", "Go."),
            ),
            ('He said "Stop." Then he left.', ('He said "Stop."', "Then he left.")),
            ("(See above.) Next one.", ("(See above.)", "Next one.")),
            ("One.\n\nTwo!?  Three", ("One.", "Two!?", "Three")),
            ("It costs 3.5 units, i.e.nothing.", ("It costs 3.5 units, i.e.nothing.",)),
            ("He paused . . . then left. Fine.", ("He paused . . .", "then left.", "Fine.")),
            ("Really? ! No.", ("Really? !", "No.")),
            ("... So it began. Yes. !", ("... So it began.", "Yes. !")),
            ("\tHello. World\n", ("Hello.", "World")),
            ("?!", ("?!",)),
            ("", ()),
        ],
    )
    def test_extract_default(self, text, expected):
        assert SentsExtractor().extract(text) == expected

    @pytest.mark.parametrize(
        ("tokenizer", "expected"),
        [(None, 2), (re.compile(r"[;.]"), 3), (str.splitlines, 1)],
    )
    def test_extract_tokenizer(self, tokenizer, expected):
        assert len(SentsExtractor(tokenizer=tokenizer).extract(TEXT)) == expected

    def test_extract_drops_empty(self):
        se = SentsExtractor(tokenizer=re.compile(r"[.]"))
        assert se.extract("The cat sleeps. The dog barks.") == ("The cat sleeps", "The dog barks")
        assert se.extract("...") == ()
        assert SentsExtractor(tokenizer=re.compile(r"\n")).extract("Cat.\n\n\nDog.") == (
            "Cat.",
            "Dog.",
        )

    def test_extract_strips(self):
        assert SentsExtractor(max_len=6).extract("\tHello. World\n") == ("Hello.", "World")
        assert SentsExtractor(tokenizer=str.splitlines).extract(" One. \n\t\n Two ") == (
            "One.",
            "Two",
        )

    @pytest.mark.parametrize(("min_len", "expected"), [(300, 0), (250, 1)])
    def test_extract_min_len(self, min_len, expected):
        assert len(SentsExtractor(min_len=min_len).extract(TEXT)) == expected

    @pytest.mark.parametrize(("max_len", "expected"), [(250, 1), (200, 0)])
    def test_extract_max_len(self, max_len, expected):
        assert len(SentsExtractor(max_len=max_len).extract(TEXT)) == expected

    @pytest.mark.parametrize(
        ("min_len", "max_len", "message"),
        [
            (10, 5, "The minimum sentence length is greater than the maximum"),
            (-1, 0, "The sentence length bounds cannot be negative"),
            (0, -1, "The sentence length bounds cannot be negative"),
            (1.5, 0, "The minimum sentence length must be an integer, not float"),
            (0, "3", "The maximum sentence length must be an integer, not str"),
        ],
    )
    def test_length_bounds(self, min_len, max_len, message):
        with pytest.raises(ParameterError, match=f"^{message}$"):
            SentsExtractor(min_len=min_len, max_len=max_len)

    @pytest.mark.parametrize("tokenizer", [666, ["a", "b"], {"a": "b"}, lambda text: 42])
    def test_extract_type_error(self, tokenizer):
        with pytest.raises(SourceTypeError):
            SentsExtractor(tokenizer=tokenizer).extract(TEXT)

    def test_extract_not_a_string(self):
        with pytest.raises(SourceTypeError, match=r"^A text string is expected, not int$"):
            SentsExtractor().extract(42)  # type: ignore[arg-type]

    def test_tokenizer_returns_strings(self):
        with pytest.raises(SourceTypeError, match=r"^The tokenizer must return strings, not int$"):
            SentsExtractor(tokenizer=lambda text: ["One.", 2]).extract(TEXT)

    def test_tokenizer_errors_propagate(self):
        def failing(text):
            raise KeyError("the tokenizer's own error")

        with pytest.raises(KeyError):
            SentsExtractor(tokenizer=failing).extract(TEXT)

    def test_sentenize_hook(self):
        class LineSents(SentsExtractor):
            def sentenize(self, text):
                return text.splitlines()

        assert LineSents().extract("One. Two.\nThree") == ("One. Two.", "Three")
        assert LineSents(tokenizer=re.compile(r"\. ")).extract("One. Two.\nThree") == (
            "One",
            "Two.\nThree",
        )


class TestWordsExtractor:
    def test_extract(self):
        we = WordsExtractor()
        assert we.extract(TEXT) == we.words
        assert len(we.words) == 85
        assert we.words[:3] == ("Thesauri", "are", "a")
        assert we.tokenizer is None

    def test_extract_default_tokenizer(self):
        text = "A well-known, don't: 3.5% of 1,500 — naïve _x_!"
        assert WordsExtractor().extract(text) == (
            "A",
            "well",
            "known",
            "don",
            "t",
            "3",
            "5",
            "of",
            "1",
            "500",
            "naïve",
            "_x_",
        )

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (unicodedata.normalize("NFD", "naïve café"), ("nai\u0308ve", "cafe\u0301")),
            ("हिन्दी भाषा", ("हिन्दी", "भाषा")),
            ("می\u200cخواهم", ("می\u200cخواهم",)),
            ("hy\u00adphen", ("hy\u00adphen",)),
            ("\ufeffThe cat", ("The", "cat")),
        ],
    )
    def test_extract_default_tokenizer_keeps_marks(self, text, expected):
        assert WordsExtractor().extract(text) == expected

    @pytest.mark.parametrize(
        ("tokenizer", "expected"),
        [(None, 85), (re.compile(r"[^\w]+"), 85), (str.split, 85)],
    )
    def test_extract_tokenizer(self, tokenizer, expected):
        assert len(WordsExtractor(tokenizer=tokenizer).extract(TEXT)) == expected

    @pytest.mark.parametrize("tokenizer", [666, ["a", "b"], {"a": "b"}])
    def test_extract_type_error(self, tokenizer):
        with pytest.raises(TypeError):
            WordsExtractor(tokenizer=tokenizer).extract(TEXT)

    def test_extract_not_a_string(self):
        with pytest.raises(SourceTypeError, match=r"^A text string is expected, not list$"):
            WordsExtractor().extract(["the", "cat"])  # type: ignore[arg-type]

    @pytest.mark.parametrize("filter_punct", [True, False])
    def test_tokenizer_returns_strings(self, filter_punct):
        we = WordsExtractor(tokenizer=spacy.blank("en").tokenizer, filter_punct=filter_punct)
        with pytest.raises(
            SourceTypeError, match=r"^The tokenizer must return strings, not Token$"
        ):
            we.extract("The cat.")

    @pytest.mark.parametrize(
        ("ngram_range", "message"),
        [
            ((2, 1), "The lower N-gram bound is greater than the upper"),
            ((0, 1), "The lower N-gram bound must be greater than 0"),
            ((-1, 1), "The lower N-gram bound must be greater than 0"),
            (2, "The N-gram range must be a pair of integers"),
            ("12", "The N-gram range must be a pair of integers"),
            ((1, 2, 3), "The N-gram range must be a pair of integers"),
            ((1.0, 2), "The lower N-gram bound must be an integer, not float"),
            ((1, 2.0), "The upper N-gram bound must be an integer, not float"),
        ],
    )
    def test_ngram_range_error(self, ngram_range, message):
        with pytest.raises(ParameterError, match=f"^{message}$"):
            WordsExtractor(ngram_range=ngram_range)

    def test_ngram_range_stored_as_tuple(self):
        we = WordsExtractor(ngram_range=[1, 2])  # type: ignore[arg-type]
        assert we.ngram_range == (1, 2)
        assert we.extract("one two") == ("one", "two", "one_two")

    @pytest.mark.parametrize(
        ("min_len", "max_len", "message"),
        [
            (10, 5, "The minimum word length is greater than the maximum"),
            (-1, 0, "The word length bounds cannot be negative"),
            (0, -3, "The word length bounds cannot be negative"),
            (1.0, 0, "The minimum word length must be an integer, not float"),
            (0, True, "The maximum word length must be an integer, not bool"),
        ],
    )
    def test_length_bounds(self, min_len, max_len, message):
        with pytest.raises(ParameterError, match=f"^{message}$"):
            WordsExtractor(min_len=min_len, max_len=max_len)

    def test_stopwords_string(self):
        with pytest.raises(SourceTypeError, match=r"^A list of stopwords is expected"):
            WordsExtractor(stopwords="the")
        with pytest.raises(SourceTypeError, match=r"not an iterator$"):
            WordsExtractor(stopwords=iter(["the"]))

    @pytest.mark.parametrize(
        ("stopwords", "message"),
        [
            ([1], "The stopwords must be strings, not int"),
            (5, "A list of stopwords is expected, not int"),
        ],
    )
    def test_stopwords_not_strings(self, stopwords, message):
        with pytest.raises(SourceTypeError, match=f"^{message}$"):
            WordsExtractor(stopwords=stopwords)

    def test_stopwords_stored_as_frozenset(self):
        assert WordsExtractor(stopwords=["A", "b"]).stopwords == frozenset({"a", "b"})
        assert WordsExtractor(stopwords={"A", "b"}).stopwords == frozenset({"a", "b"})
        assert WordsExtractor(stopwords={"a": 1}).stopwords == frozenset({"a"})
        assert WordsExtractor(stopwords=[]).stopwords is None
        assert WordsExtractor().stopwords is None

    def test_extract_stopwords_case_insensitive(self):
        text = "The thesauri. A difference between the thesauri."
        assert WordsExtractor(stopwords=["THE", "a"]).extract(text) == (
            "thesauri",
            "difference",
            "between",
            "thesauri",
        )

    def test_extract_stopwords_after_lowercase(self):
        we = WordsExtractor(stopwords=["no", "and"], lowercase=True)
        text = "No money, and no friends. And no more."
        assert we.extract(text) == ("money", "friends", "more")

    @pytest.mark.parametrize(
        ("stopwords", "expected"),
        [(["the", "of", "a", "and"], 56), ({"meanings"}, 80)],
    )
    def test_extract_stopwords(self, stopwords, expected):
        assert len(WordsExtractor(stopwords=stopwords).extract(TEXT)) == expected

    @pytest.mark.parametrize(
        ("token", "is_number"),
        [
            ("100", True),
            ("-5", True),
            ("+7", True),
            ("−5", True),
            ("1990-1995", True),
            ("1,500.50", True),
            ("1.500,50", True),
            ("12/03/2020", True),
            ("3:30", True),
            ("10%", True),
            ("-5.5%", True),
            ("٣", True),
            ("3rd", False),
            ("1990s", False),
            ("x1", False),
            ("−x", False),
            ("5-year", False),
            ("word", False),
        ],
    )
    def test_extract_filter_nums(self, token, is_number):
        we = WordsExtractor(tokenizer=str.split, filter_nums=True)
        expected = ("word", "word") if is_number else ("word", token, "word")
        assert we.extract(f"word {token} word") == expected

    def test_extract_filter_punct(self):
        text = "What?! Yes!!! No... Word -- word … 5 % « quoted » “here” 100 € №"
        expected = ("What?!", "Yes!!!", "No...", "Word", "word", "5", "quoted", "“here”", "100")
        assert WordsExtractor(tokenizer=str.split).extract(text) == expected
        assert len(WordsExtractor(tokenizer=str.split, filter_punct=False).extract(text)) == 16

    def test_extract_drops_empty(self):
        we = WordsExtractor(tokenizer=re.compile(r"\W+"), filter_punct=False)
        assert we.extract("Hello, world.") == ("Hello", "world")
        assert we.extract("") == ()
        we = WordsExtractor(tokenizer=re.compile(" "), filter_punct=False)
        assert we.extract("one two \n three\t") == ("one", "two", "three\t")

    def test_extract_pattern_with_groups(self):
        we = WordsExtractor(tokenizer=re.compile(r"(,)|;"), filter_punct=False)
        assert we.extract("a,b;c") == ("a", ",", "b", "c")
        assert SentsExtractor(tokenizer=re.compile(r"(!)|\.")).extract("One. Two!") == (
            "One",
            "Two",
            "!",
        )

    def test_extract_use_lexemes_default(self):
        assert WordsExtractor(use_lexemes=True).extract("Cats sleep") == ("Cats", "sleep")

    @pytest.mark.parametrize(("min_len", "expected"), [(6, 37), (3, 68)])
    def test_extract_min_len(self, min_len, expected):
        assert len(WordsExtractor(min_len=min_len).extract(TEXT)) == expected

    @pytest.mark.parametrize(("max_len", "expected"), [(6, 53), (3, 39)])
    def test_extract_max_len(self, max_len, expected):
        assert len(WordsExtractor(max_len=max_len).extract(TEXT)) == expected

    def test_extract_ngram_range(self):
        we = WordsExtractor(ngram_range=(1, 3))
        assert len(we.extract(TEXT)) == 85 + 84 + 83
        assert "formal_ontologies_lies" in we.words
        assert WordsExtractor(ngram_range=(2, 2)).extract("one two three") == (
            "one_two",
            "two_three",
        )
        assert WordsExtractor(ngram_range=(2, 3)).extract("one") == ()

    def test_get_most_common(self):
        we = WordsExtractor()
        we.extract(TEXT)
        assert we.get_most_common(2) == [("the", 15), ("of", 9)]
        with pytest.raises(ParameterError, match=r"^The number of words must be greater than 0$"):
            we.get_most_common(0)
        with pytest.raises(
            ParameterError, match=r"^The number of words must be an integer, not float$"
        ):
            we.get_most_common(2.0)  # type: ignore[arg-type]

    def test_hooks(self):
        class Language(WordsExtractor):
            number_pattern = re.compile(r"\d+(?:st|nd|rd|th)?")

            def tokenize(self, text):
                return text.split()

            def lemmatize(self, word):
                return word.lower().removesuffix("s")

        we = Language(filter_nums=True, use_lexemes=True)
        assert we.extract("The 3rd Cats, 5 dogs") == ("the", "cats,", "dog")
        assert Language(tokenizer=re.compile(r"\W+")).extract("3rd cats") == ("3rd", "cats")
        assert NUMBER_PATTERN.fullmatch("3rd") is None

    def test_static_hooks(self):
        class Upper(WordsExtractor):
            lemmatize = staticmethod(str.upper)

        assert Upper(use_lexemes=True).extract("cat dog") == ("CAT", "DOG")


class TestCharNgramsExtractor:
    text = "The cat slept  on the sill,\nand the dog - on the floor."

    def test_extract(self):
        ce = CharNgramsExtractor()
        ngrams = ce.extract(self.text)
        assert ngrams[:8] == ("Th", "he", "e ", " c", "ca", "at", "t ", " s")
        assert len(ngrams) == len(" ".join(self.text.split())) - 1
        assert ce.ngrams == ngrams
        assert ce.tokenizer is None
        assert CharNgramsExtractor(n=1).extract("ñu") == ("ñ", "u")
        assert CharNgramsExtractor(n=4).extract("ñu") == ()
        assert CharNgramsExtractor().extract("") == ()

    def test_lowercase(self):
        ce = CharNgramsExtractor(n=3, lowercase=True)
        assert ce.extract(self.text)[:6] == ("the", "he ", "e c", " ca", "cat", "at ")
        assert ce.get_most_common(2) == [("the", 4), ("he ", 4)]

    def test_within_words(self):
        ce = CharNgramsExtractor(n=4, lowercase=True, within_words=True)
        assert ce.extract(self.text) == ("slep", "lept", "sill", "floo", "loor")
        ce = CharNgramsExtractor(n=2, within_words=True, tokenizer=re.compile(r"[\s,.-]+"))
        assert ce.extract("Cat - ñu") == ("Ca", "at", "ñu")
        ce = CharNgramsExtractor(n=2, within_words=True, tokenizer=str.split)
        assert ce.extract("Cat ?! ñu") == ("Ca", "at", "ñu")
        ce = CharNgramsExtractor(n=3, within_words=True)
        assert ce.extract(unicodedata.normalize("NFD", "café")) == ("caf", "afe", "fe\u0301")

    def test_tokenize_hook(self):
        class Spaces(CharNgramsExtractor):
            def tokenize(self, text):
                return text.split(" ")

        assert Spaces(n=3, within_words=True).extract("don't go") == ("don", "on'", "n't")
        assert CharNgramsExtractor(n=3, within_words=True).extract("don't go") == ("don",)

    def test_errors(self):
        with pytest.raises(ParameterError, match=r"^The N-gram length must be greater than 0$"):
            CharNgramsExtractor(n=0)
        with pytest.raises(
            ParameterError, match=r"^The number of N-grams must be greater than 0$"
        ):
            CharNgramsExtractor().get_most_common(0)
        with pytest.raises(
            ParameterError, match=r"^The N-gram length must be an integer, not float$"
        ):
            CharNgramsExtractor(n=2.0)  # type: ignore[arg-type]
        with pytest.raises(
            ParameterError, match=r"^The number of N-grams must be an integer, not float$"
        ):
            CharNgramsExtractor().get_most_common(1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            CharNgramsExtractor(within_words=True, tokenizer=42).extract(self.text)
        for within_words in (False, True):
            with pytest.raises(SourceTypeError, match=r"^A text string is expected, not int$"):
                CharNgramsExtractor(within_words=within_words).extract(42)  # type: ignore[arg-type]
