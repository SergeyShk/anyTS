# Migrating from 0.4

Since 0.5 every source is read through a [document](https://sergeyshk.github.io/anyTS/document/) of [anySeg](https://github.com/SergeyShk/anySeg): a string, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) and a `Document` give one document, and its tokens decide what a word is. The core no longer bridges a string and a `Doc`, and the hooks of a language library take the document and the words of its tree instead of spaCy objects. This page lists what code written for 0.4 changes.

## Removed names { #removed }

| Removed | Replacement |
| :------ | :---------- |
| `anyts.utils.add_tokenizer_rules` | the tokenizer of anySeg in a pipeline: `anyseg.Tokenizer.v1` in the config |
| `anyts.components.start_sents_after_blank_lines` | the component `anyseg_sentencizer` of anySeg; the document of a `Doc` starts a sentence after every blank line anyway |
| `anyts.utils.set_sent_starts` | `to_document(text, sentenize=...)`, or the sentences of `anyseg_sentencizer` in a pipeline |
| `anyts.utils.joins_previous`, `iter_doc_tokens`, `iter_doc_units`, `iter_doc_words`, `split_doc_units` | the words of the document: `document_words(to_document(doc))`, `get_tree(...).words` |
| `anyts.utils.find_unit_marks`, `find_unit_paragraph_starts` | `find_marks` and `find_paragraph_starts` on the text |
| `anyts.utils.has_sents` | `doc.has_annotation("SENT_START", require_complete=True)` |
| `anyts.utils.has_pos`, `is_word` | the columns of the document (`document.column("upos")`), `has_words(token.text)` |
| `from anyts.extractors import BLANK_LINE` | `from anyts.utils import BLANK_LINE` |

A pipeline with the tokenizer of spaCy and a parser has no replacement for the first three: the tokenizer and the sentencizer of anySeg segment the text otherwise, so the parser builds other trees and the numbers shift. A library keeps its own copies of them until it moves to the pipeline of anySeg. The tokenizer of anySeg goes into the config of the pipeline (`spacy.blank(lang, config={"nlp": {"tokenizer": {"@tokenizers": "anyseg.Tokenizer.v1"}}})`): a pipeline with one set as `nlp.tokenizer` is saved by `nlp.to_disk` without it, and `spacy.load` fails on it (`FileNotFoundError`).

## Class attributes and hooks { #hooks }

The attributes of 0.4 that the core no longer reads raise `ParameterError` (the message `removed_attribute`) when a class that sets them is defined, since a class that kept them would give other numbers without a sign:

| Removed | Classes | Replacement |
| :------ | :------ | :---------- |
| `words_extractor_class` | `BasicStats`, `StyleStats`, `PhonStats` | `parse` to segment a string in the language, `doc_words` to normalize the forms of its words |
| `sents_extractor_class` | `BasicStats`, `CohesionStats` | `parse` |
| `join_hyphens` | `BasicStats`, `StyleStats`, `PhonStats`, `SyntaxStats`, `CohesionStats`, `LexicalStatsComponent` | the tokens of the document: `parse` of the class, or the tokenizer of the pipeline |
| `doc_units` | `CohesionStats` | `analyze`, `word_info` |
| `iter_words`, `iter_sents` | `HighlightedText` | `parse`, `doc_words` |

The parameter `join_hyphens` is gone from `kwic`, `sentence_lengths`, `sentence_lengths_plot` and the functions of `anyts.syntax_stats` as well. The hooks that remain take other arguments:

- `doc_words(document)` of `StyleStats`, `PhonStats` and `HighlightedText` takes a `Document` instead of a `Doc`; `get_doc_words` and `iter_doc_sents` too.
- `word_info(word)` of `CohesionStats` takes a `TreeWord` instead of a list of tokens. The hooks of `SyntaxStats` and the functions of `anyts.syntax_stats` take a `TreeWord` instead of a `Token`, and `dependency_triples(words)` a sequence of them; so do `has_feature`, `is_finite_verb` and `is_infinitive` of `anyts.utils`, and `tokens_span` and `find_split_predicate_highlights` of `anyts.visualizers.highlight`. `SyntaxStats.parse` returns a `Document`, such as `to_document` of a parsed `Doc`.
- The `analyze` of `MorphStats`, `LexicalStats` and `CohesionStats` gets a `Document` too, and the default reads the document of `parse`, so a library that annotated a string in its `analyze` moves that into `parse`. `CohesionStats` checks the parts of speech and the lemmas by `requires_pos` and `requires_lemmas`, which a library whose `word_info` annotates the words itself turns off.
- `find(document)` of `HighlightedText` gets the document instead of a `Doc` or `None`, and `layer_annotations` names the columns of the document: `DEP` - `deprel`, `POS` - `upos`, `LEMMA` - `lemma`, `MORPH` - `feats`, `TAG` - `xpos`; the named entities are gone. `annotation_names` takes the same columns as keys (`head` and `deprel` for the parse), and the keys of 0.4 are not read.
- `lemmatize` of `kwic` gets the words of Universal Dependencies of a token (`Word` of anySeg with `form`, `lemma`, `upos` and `feats`, the string of CoNLL-U such as `Case=Nom|Number=Sing`) instead of spaCy tokens, and the third item of a `tokenize` triple is not read.
- `get_stats(flat=True)` takes `flat` as a keyword only.

## Words of the tree { #tree-words }

The words of the tree of a document (`get_tree`) are `TreeWord` objects in place of spaCy tokens:

| `Token` | `TreeWord` |
| :------ | :--------- |
| `text`, `lower_` | `form`, `form.lower()` |
| `lemma_`, `pos_`, `tag_` | `lemma`, `upos`, `xpos`: `None` without a value, not an empty string |
| `dep_` | `deprel`; the root of a spaCy parse is `root`, not `ROOT` |
| `morph.get(name)` | `feats.get(name)`: the values joined by commas (`Int,Rel`), `None` without the feature; `has_feature(word, name, value)` checks one value, and `feats` is not to be changed |
| `morph.to_dict()`, `str(morph)` | `feats`, the column `feats` of the document (`Case=Nom|PronType=Int,Rel`) |
| `has_morph()` | none for a word: one annotated with no features and one never annotated both have empty `feats`; `bool(feats)` says whether a word has features, `doc.has_annotation("MORPH")` whether the `Doc` was annotated |
| `doc`, `i`, `doc[i]` | `tree`, `index`, `tree.words[i]`: the positions of the words differ from `Token.i` where a `Doc` has tokens of whitespace or of invisible separators alone, or multiword tokens whose words carry columns, and `tree.word_at(token.idx, token.idx + len(token))` gives the word of a token |
| `nbor(n)` | `tree.words[word.index + n]` |
| `idx` | `start`, after `idx` where the token starts with a separator the document leaves out, such as a byte order mark; `end` is the end of the token, shared by the words of a multiword token |
| `head` | `head`, `None` at the head of a sentence instead of the token itself |
| `children`, `subtree` | `children` (punctuation marks included), `get_subtree(word)` of `anyts.syntax_stats` |
| `left_edge`, `right_edge` | `get_subtree(word)[0]`, `get_subtree(word)[-1]` |
| `sent`, `sent.start`, `sent.end`, `is_sent_start` | `tree.sentences[word.sentence]`, its first and last word; `sentence` is its position |
| `is_punct` | `is_punctuation(word.form)` of `anyts.utils`, symbols included |
| `is_space`, `whitespace_` | none: whitespace is no word of the tree, and the text between two words is `tree.text[first.end:second.start]` |

## Sources and segmentation { #segmentation }

- A blank line ends a sentence of every source, a `Doc` with its own sentences included, so a sentence of a parser over a blank line is split: of the words that hung over the line, the first heads the new sentence and the others hang on it with `dep`. A blank line is that of anySeg: the vertical tab and the form feed break a line, and a line of separators alone is blank.
- The tokens of the document decide what a word is: the tokenizer of spaCy splits `well-known` into three tokens in English or Russian and the words stay split, and so do the default tokens of a string; the tokenizer of anySeg keeps it whole. A multiword token of anySeg (`token._.anyseg_words`) gives its words of Universal Dependencies to `MorphStats`, `LexicalStats` and the tree; without columns of their own they are one word with the columns of the token.
- `SyntaxStats`, `CohesionStats` and `MorphStats` take a string, which a library annotates in `parse`: with the default `parse` a string raises `SourceError` (`no_parse`, `no_pos`) instead of `SourceTypeError`. `LexicalStats` can be used without a subclass, given a dictionary.
- `to_document` returns the same `Document` for an unchanged `Doc` in a thread, and `get_tree` the same tree: neither is to be changed, and code that needs other columns builds a document of its own.

## Messages { #messages }

A library that merges its messages over the defaults (`{**MESSAGES, **own}`) gets the new keys in English until it translates them, and drops the removed ones, which `check_messages` refuses:

- removed: `hook_doc`, `hook_spans`;
- new: `bool_param`, `integer_param`, `number_param`, `words_param`, `connector_words`, `connector_sent_index`, `connector_pos_list`, `connector_breaks_type`, `connector_blocked_type`, `document_tokens`, `hook_document`, `hook_bounds`, `hook_words`, `hook_word_pairs`, `hook_string`, `layer_columns`, `matcher_class`, `mark_length`, `negative_words`, `empty_extension`, `removed_attribute`;
- changed: `layer_annotations` speaks of a document.

The errors of the parameters of a wrong type name the parameter as in the signature under a generic key: `The top_n must be an integer, not str` instead of `The number of the most frequent words must be an integer, not str`.
