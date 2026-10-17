# Labels and messages

!!! info ""
    **anyts.utils**

The labels of the plots and the messages of the errors that a language library passes over the English defaults.

## merge_labels

<!-- --8<-- [start:merge_labels] -->
Merges the labels given for a plot over its default ones; a label not given keeps its default. A default with fields in braces, such as `"Moving average ({window})"`, is a format string: a label given for it may use only those fields, with a literal brace doubled (`{{`), and is tried on sample values of the fields, so that a format spec the values do not take (`{window:s}` for a number) fails before a figure is created. The other labels are taken as they are. Labels that are not a mapping of strings, or have an unknown key, a field their default lacks or a format spec their values do not take, raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `defaults` | dict[str, str] | `-` | Default labels by key |
| `labels` | dict[str, str] | `-` | Labels given; `None` - the default ones |
| `**samples` | object | `-` | Values of the fields of the format labels, for trying the labels given |
<!-- --8<-- [end:merge_labels] -->

The defaults of the visualizers of the core are `anyts.constants.VISUALIZER_LABELS`, by the name of the function.

!!! example "Example"

    ``` python
    from anyts.utils import merge_labels

    merge_labels({"title": "Plot", "xlabel": "x"}, {"title": "My plot"})
    # {'title': 'My plot', 'xlabel': 'x'}
    ```

## check_messages

<!-- --8<-- [start:check_messages] -->
Checks the messages of the errors a class of statistics raises: they must be complete, a string for every key of the defaults, so that an error never turns into a `KeyError`, and a message whose default has fields in braces may use only those fields, with a literal brace doubled (`{{`). The classes of statistics check the `messages` of a subclass when it is defined. Messages that are not a mapping of strings, lack a key, have an unknown one or a field their default lacks raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `messages` | dict[str, str] | `-` | Messages by key |
| `defaults` | dict[str, str] | `MESSAGES` | Default messages by key |
<!-- --8<-- [end:check_messages] -->
