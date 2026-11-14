# Document model

The classes of statistics read a text through a document of [anySeg](https://github.com/SergeyShk/anySeg): its tokens with their positions, the words of Universal Dependencies with their columns (lemma, part of speech, features, head and relation), its sentences and paragraphs. A string, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) and a ready `Document` give one document, so a text split the same way gives the same numbers in every form. A language library segments and annotates a string in its language by the `parse` hook of the classes; the core splits a string into words of `\w`, punctuation marks and the sentences of `SentsExtractor`.

## Document of a source { #to_document }

<!-- --8<-- [start:to_document] -->
``` {.python .signature}
to_document(source, tokenize=None, sentenize=None, *, messages=MESSAGES)
```

Returns the document of a data source in the model of anySeg. A `Document` is returned as it is. A `Doc` keeps its tokens, their columns and its sentences; a `Doc` with no or only partial sentence starts (`has_sents`) and no parse gets the sentences of `sentenize` on its text. A string is split into tokens by `tokenize` and into sentences by `sentenize`, which may give them in any order since only their starts count, and the default tokens fill the gaps between those of `tokenize`, so a tokenizer may give the words alone. A blank line (`BLANK_LINE`) ends a paragraph of the document and so a sentence, of a `Doc` too: every part between blank lines goes to `sentenize` apart, and a sentence starts at its first token. Whitespace and invisible separators (the soft hyphen, zero-width characters, the byte order mark) at the edges of a token are left out, and a token of nothing else is dropped.

The default tokens are the words of `WordsExtractor` and every run of one other character, such as `...` or `--`; the default sentences are those of `SentsExtractor`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `Document` | - | Data source |
| `tokenize` | `Callable` | `None` | Tokenizer giving the start, the end and the text of every token of a string |
| `sentenize` | `Callable` | `None` | Splitter giving the start, the end and the text of every sentence of a string |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key |

A source that is neither a string, a `Doc` nor a `Document` raises `SourceTypeError` (a `Span` with the message `source_span`), and so does a `tokenize` or `sentenize` that cannot be called, does not give triples of integer bounds within the text and a string (ascending for `tokenize`), or gives a token over a blank line. A `Doc` with a token over a blank line, as a retokenizer may merge, or with words in `token._.anyseg_words` that a document cannot hold raises `SourceError` with the message `document_tokens`.
<!-- --8<-- [end:to_document] -->

=== "Code"

    ``` python
    import spacy

    from anyts.document import to_document

    document = to_document("The cat sat. It slept!\n\nThe end")
    [token.text for token in document.tokens][:4]
    [sentence.text for sentence in document.sentences]

    doc = spacy.blank("en")("One. Two!")
    [sentence.text for sentence in to_document(doc).sentences]
    ```

=== "Result"

    ```
    ['The', 'cat', 'sat', '.']
    ['The cat sat.', 'It slept!', 'The end']
    ['One.', 'Two!']
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

## Document objects { #is_document }

<!-- --8<-- [start:is_document] -->
``` {.python .signature}
is_document(value)
```

Checks whether a value is a `Document` object of anySeg without importing anySeg, as `is_doc` does for spaCy: such an object exists only once anySeg is loaded, so before that every value gives `False`.

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

Returns the dependency tree of a document: its words of Universal Dependencies with the columns `lemma`, `upos`, `xpos`, `feats`, `head` and `deprel`, linked by their heads within their sentences. A word without a head heads its sentence. The syntactic statistics and their language hooks read the words of this tree. A value that is not a `Document` raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `document` | `Document` | - | Document of anySeg |

The result is a `Tree` named tuple: `text`, `words` - the words of the document, punctuation marks included - and `sentences` - the words of every sentence.
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
| `feats` | `dict[str, str]` | Features by name, the values of a feature of several joined by commas (`Int,Rel`); the words of one set of features share one mapping |
| `deprel` | `str` / `None` | Relation to the head; the root of a spaCy parse is `root` |
| `head` | `TreeWord` / `None` | Word it hangs on, `None` at the head of a sentence |
| `children` | `tuple[TreeWord]` | Words hanging on it, in the order of the text |
| `sentence` | `int` | Position of its sentence |
| `start`, `end` | `int` | Positions of its token in the text; the words of a multiword token share them |
| `tree` | `Tree` | Tree of the document, for the words around it (`word.tree.words[word.index - 1]`) |

In place of the attributes of a spaCy `Token`: `text` - `form`, `lemma_` - `lemma`, `pos_` - `upos`, `tag_` - `xpos`, `dep_` - `deprel`, `morph.get(name)` - `feats.get(name)` (a string), `i` - `index`, `idx` - `start`, `head` of a root - `None` instead of the token itself.
<!-- --8<-- [end:TreeWord] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.document import get_tree, to_document

    doc = Doc(
        spacy.blank("en").vocab,
        words=["Cats", "sleep", "."],
        heads=[1, 1, 1],
        deps=["nsubj", "ROOT", "punct"],
        pos=["NOUN", "VERB", "PUNCT"],
        morphs=["Number=Plur", "Mood=Ind|VerbForm=Fin", ""],
    )
    cats, sleep, mark = get_tree(to_document(doc)).words
    cats.head.form, sleep.head, sleep.deprel, sleep.feats["VerbForm"]
    sleep.children
    ```

=== "Result"

    ```
    ('sleep', None, 'root', 'Fin')
    (TreeWord(0, 'Cats', NOUN, nsubj), TreeWord(2, '.', PUNCT, punct))
    ```
