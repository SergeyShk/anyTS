# Document model

The classes of statistics read a text through a document of [anySeg](https://github.com/SergeyShk/anySeg): its tokens with their positions, the words of Universal Dependencies with their columns (lemma, part of speech, features, head and relation), its sentences and paragraphs. The classes take a string or a ready `Document`, and a text split the same way gives the same numbers in either form. A language library segments and annotates a string in its language by the `parse` hook of the classes; the core splits a string into words of `\w`, punctuation marks and the sentences of `SentsExtractor`.

## Document of a source { #to_document }

<!-- --8<-- [start:to_document] -->
``` {.python .signature}
to_document(source, tokenize=None, sentenize=None, *, messages=MESSAGES)
```

Returns the document of a data source in the model of anySeg. A `Document` is returned as it is. A string is split into tokens by `tokenize` and into sentences by `sentenize`, which may give them in any order since only their starts count, and the default tokens fill the gaps between those of `tokenize`, so a tokenizer may give the words alone. A blank line (`BLANK_LINE`) ends a paragraph of the document and so a sentence: every part between blank lines goes to `sentenize` apart, and a sentence starts at its first token. Whitespace and invisible separators (the soft hyphen, zero-width characters, the byte order mark, the marks of the direction of text) at the edges of a token are left out, and a token of nothing else is dropped; a word joiner or a mark of the direction inside a word, as anySeg keeps it, is part of the word.

The default tokens are the words of `WordsExtractor` and every run of one other character, such as `...` or `--`; the default sentences are those of `SentsExtractor`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Document` | - | Data source |
| `tokenize` | `Callable` | `None` | Tokenizer giving the start, the end and the text of every token of a string |
| `sentenize` | `Callable` | `None` | Splitter giving the start, the end and the text of every sentence of a string |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key |

A source that is neither a string nor a `Document` raises `SourceTypeError`, and so does a `tokenize` or `sentenize` that cannot be called, does not give triples of integer bounds within the text and a string (ascending for `tokenize`; the message `hook_bounds`), or gives a token over a blank line (`document_tokens`).
<!-- --8<-- [end:to_document] -->

=== "Code"

    ``` python
    from anyts.document import to_document

    document = to_document("The cat sat. It slept!\n\nThe end")
    [token.text for token in document.tokens][:4]
    [sentence.text for sentence in document.sentences]
    ```

=== "Result"

    ```
    ['The', 'cat', 'sat', '.']
    ['The cat sat.', 'It slept!', 'The end']
    ```

## Words of a document { #document_words }

<!-- --8<-- [start:document_words] -->
``` {.python .signature}
document_words(document)
```

Returns the words of a document: its tokens with a letter or a digit (`str.isalnum`), as written, so that no punctuation mark, symbol or character of no class, such as a bullet of private use in a text from a PDF, is a word. A multiword token, such as Spanish `del` of the words `de` and `el`, is one word. A value that is not a `Document` raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `document` | `Document` | - | Document of anySeg |
<!-- --8<-- [end:document_words] -->

=== "Code"

    ``` python
    from anyts.document import document_words, to_document

    document_words(to_document("Well, the cat sat - 100%!"))
    ```

=== "Result"

    ```
    ('Well', 'the', 'cat', 'sat', '100')
    ```

## Part of a document { #document_part }

<!-- --8<-- [start:document_part] -->
``` {.python .signature}
document_part(document, start, end, *, messages=None)
```

Returns the document of a part of a document: the sentences the span of the text from `start` to `end` overlaps, whole, so that their trees stay whole - a sentence, a paragraph or a fragment of several of them. Its text runs from the first token of the first sentence to the last token of the last one, and the positions count from there. The tokens, the words with their columns, the sentences and the paragraphs are those of the document, and a head stays as it is, since the head of a word is in its own sentence. A class of statistics counts a part as any document. Every call reads the columns of the whole document, so [`by_parts`](https://sergeyshk.github.io/anyTS/stats/stats/#by_parts), which reads them once, counts every sentence, line or paragraph of a text.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `document` | `Document` | - | Document of anySeg |
| `start` | `int` | - | Position of the first character of the span in the text |
| `end` | `int` | - | Position after its last character |
| `messages` | `dict[str, str]` | `None` | Messages of the errors by key, in place of those of the library |

A value that is not a `Document` raises `SourceTypeError`; a `start` or an `end` that is not an integer, or a span not within the text with its start before its end, `ParameterError`; and a span that overlaps no sentence, as one of whitespace between two, `SourceError`.
<!-- --8<-- [end:document_part] -->

=== "Code"

    ``` python
    from anyts.document import document_part, to_document

    document = to_document("The cat sleeps. The dog barks.\n\nA bird sings.")
    document_part(document, 20, 21).text
    [sentence.text for sentence in document_part(document, 5, 35).sentences]
    ```

=== "Result"

    ```
    'The dog barks.'
    ['The cat sleeps.', 'The dog barks.', 'A bird sings.']
    ```

## Document objects { #is_document }

<!-- --8<-- [start:is_document] -->
``` {.python .signature}
is_document(value)
```

Checks whether a value is a `Document` object of anySeg without importing anySeg: such an object exists only once anySeg is loaded, so before that every value gives `False`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
<!-- --8<-- [end:is_document] -->

=== "Code"

    ``` python
    from anyseg import Document

    from anyts.utils import is_document

    is_document(Document.from_tokens("The cat", [0, 4], [3, 7])), is_document("The cat")
    ```

=== "Result"

    ```
    (True, False)
    ```

## Dependency tree { #get_tree }

<!-- --8<-- [start:get_tree] -->
``` {.python .signature}
get_tree(document)
```

Returns the dependency tree of a document: its words of Universal Dependencies with the columns `lemma`, `upos`, `xpos`, `feats`, `head` and `deprel`, linked by their heads within their sentences. A word without a head heads its sentence. The syntactic statistics and their language hooks read the words of this tree. The tree of the document a command or a report counts is built once and shared by its classes, and it is not to be changed.

The words of a tree refer to each other and to the tree, so an unused tree waits for the garbage collector of Python rather than going at once: a loop over many large texts may hold several of them, and `gc.collect()` between the texts frees them. A value that is not a `Document` raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `document` | `Document` | - | Document of anySeg |

The result is a `Tree` named tuple: `text`, `words` - the words of the document, punctuation marks included - and `sentences` - the words of every sentence. Its method `word_at(position, end=None)` gives the word whose token covers a position of the text, or with `end` the first one whose token overlaps the span; the first word of a multiword token, or `None` where no word stands, as at whitespace.
<!-- --8<-- [end:get_tree] -->

<!-- --8<-- [start:TreeWord] -->
``` {.python .signature}
TreeWord
```

A word of the tree, with the names of Universal Dependencies and its place in the tree:

| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `index` | `int` | Position among the words of the document |
| `form` | `str` | Form of the word |
| `lemma` | `str` / `None` | Lemma |
| `upos` | `str` / `None` | Part of speech of Universal Dependencies |
| `xpos` | `str` / `None` | Tag of the language |
| `feats` | `Mapping[str, str]` | Features by name, the values of a feature of several joined by commas (`Int,Rel`); the words of one set of features share one mapping, which is not to be changed |
| `deprel` | `str` / `None` | Relation to the head |
| `head` | `TreeWord` / `None` | Word it hangs on, `None` at the head of a sentence |
| `children` | `tuple[TreeWord]` | Words hanging on it, in the order of the text |
| `sentence` | `int` | Position of its sentence |
| `start`, `end` | `int` | Positions of its token in the text; the words of a multiword token share them |
| `tree` | `Tree` | Tree of the document, for the words around it (`word.tree.words[word.index - 1]` for a word after the first) |
<!-- --8<-- [end:TreeWord] -->

=== "Code"

    ``` python
    from anyseg import Document

    from anyts.document import get_tree

    document = Document.from_tokens("Cats sleep.", [0, 5, 10], [4, 10, 11])
    document.set_columns(
        upos=["NOUN", "VERB", "PUNCT"],
        feats=["Number=Plur", "Mood=Ind|VerbForm=Fin", None],
        head=[2, 0, 2],
        deprel=["nsubj", "root", "punct"],
    )
    cats, sleep, mark = get_tree(document).words
    cats.head.form, sleep.head, sleep.deprel, sleep.feats["VerbForm"]
    sleep.children
    ```

=== "Result"

    ```
    ('sleep', None, 'root', 'Fin')
    (TreeWord(0, 'Cats', NOUN, nsubj), TreeWord(2, '.', PUNCT, punct))
    ```
