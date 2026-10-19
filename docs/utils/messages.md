# Labels and messages

The labels of the plots and the messages of the errors that a language library passes over the English defaults.

## Labels of a plot { #merge_labels }

<!-- --8<-- [start:merge_labels] -->
``` {.python .signature}
merge_labels(defaults, labels, **samples)
```

Merges the labels given for a plot over its default ones; a label not given keeps its default. A default with fields in braces, such as `"Moving average ({window})"`, is a format string: a label given for it may use only those fields, with a literal brace doubled (`{{`), and is tried on sample values of the fields, so that a format spec the values do not take (`{window:s}` for a number) fails before a figure is created. The other labels are taken as they are.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `defaults` | `dict[str, str]` | - | Default labels by key |
| `labels` | `dict[str, str]` | - | Labels given; `None` - the default ones |
| `**samples` | `object` | - | Values of the fields of the format labels, for trying the labels given |

Labels that are not a mapping of strings or have an unknown key raise `ParameterError`, and so does a label of a format default that is not a format string or has a field its default lacks or a format spec its values do not take.
<!-- --8<-- [end:merge_labels] -->

The defaults of the visualizers of the core are `anyts.constants.VISUALIZER_LABELS`, by the name of the function.

=== "Code"

    ``` python
    from anyts.utils import merge_labels

    merge_labels({"title": "Plot", "xlabel": "x"}, {"title": "My plot"})
    merge_labels({"title": "Moving average ({window})"}, {"title": "Window of {size}"}, window=100)
    ```

=== "Result"

    ```
    {'title': 'My plot', 'xlabel': 'x'}
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The label 'title' has unknown fields ['size']; available fields: ['window']
    ```

## Messages of the errors { #check_messages }

<!-- --8<-- [start:check_messages] -->
``` {.python .signature}
check_messages(messages, defaults=MESSAGES)
```

Checks the messages of the errors a class of statistics raises: they must be complete, a string for every key of the defaults, so that an error never turns into a `KeyError`, and a message whose default has fields in braces may use only those fields, with a literal brace doubled (`{{`). The classes of statistics check the `messages` of a subclass when it is defined.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `messages` | `dict[str, str]` | - | Messages by key |
| `defaults` | `dict[str, str]` | `MESSAGES` | Default messages by key |

Messages that are not a mapping of strings, lack a key or have an unknown one raise `ParameterError`, and so does a message of a format default that is not a format string or has a field its default lacks.
<!-- --8<-- [end:check_messages] -->

=== "Code"

    ``` python
    from anyts.constants import MESSAGES
    from anyts.utils import check_messages

    check_messages({**MESSAGES, "no_words": "Il testo non contiene parole"})
    check_messages({**MESSAGES, "text_type": "Testo atteso, non {kind}"})
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The message 'text_type' has unknown fields ['kind']; available fields: ['type']
    ```
