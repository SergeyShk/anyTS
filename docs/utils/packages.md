# Lazy packages

A package that imports its names on first use, so a light name does not load the dependencies of a heavy one.

## Lazy import { #make_lazy }

<!-- --8<-- [start:make_lazy] -->
``` {.python .signature}
make_lazy(name, modules)
```

Turns a package into a `LazyPackage`: every name of the mapping `modules` is imported from its module of the package when it is first read. Importing the package then loads only what it imports itself, so the highlighting does not load matplotlib and a module of statistics does not load spaCy with the components. A module of the package is also its attribute on first use, and a module named as one of its functions (*zipf*) leaves the function under that name. A package calls it at the end of its `__init__` with `__name__`; a `TYPE_CHECKING` block imports the same names for the type checkers.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `name` | `str` | - | Name of the package, imported |
| `modules` | `dict[str, str]` | - | Module of the package by name |

A name that is not a string or a mapping that is not one of strings to strings raises `SourceTypeError`; a name that is not that of an imported package, a lazy name that is not an identifier and a module that is not a dotted name of identifiers raise `ParameterError`.
<!-- --8<-- [end:make_lazy] -->

``` {.python .fragment}
# The __init__ of a package
from typing import TYPE_CHECKING

from anyts.utils import make_lazy

if TYPE_CHECKING:
    from .highlight import Highlight
    from .zipf import zipf

__all__ = ["Highlight", "zipf"]

make_lazy(__name__, {"Highlight": "highlight", "zipf": "zipf"})
```

=== "Code"

    ``` python
    import sys

    import anyts.visualizers as visualizers

    type(visualizers).__name__, "anyts.visualizers.zipf" in sys.modules
    visualizers.zipf.__module__, "anyts.visualizers.zipf" in sys.modules
    ```

=== "Result"

    ```
    ('LazyPackage', False)
    ('anyts.visualizers.zipf', True)
    ```

## Class of a lazy package { #LazyPackage }

<!-- --8<-- [start:LazyPackage] -->
`LazyPackage` is the class of a package after `make_lazy`, a subclass of `types.ModuleType`. It imports a name of its mapping on first read and keeps it as its attribute, gives a module of the package as an attribute, and lists the names of the mapping in `dir()`: those of `__all__` if the package has it, so that `help()` and `inspect.getmembers()` import only the public names. A name that is neither raises `AttributeError`, a module that fails to import for a missing dependency raises its `ModuleNotFoundError`, and an `AttributeError` raised while a module imports comes as an `ImportError` with it as the cause, since Python would take it for a missing name.
<!-- --8<-- [end:LazyPackage] -->

=== "Code"

    ``` python
    "heaps_plot" in dir(visualizers), "anyts.visualizers.vocabulary" in sys.modules
    visualizers.vocabulary.__name__
    visualizers.zipf_plot
    ```

=== "Result"

    ```
    (True, False)
    'anyts.visualizers.vocabulary'
    Traceback (most recent call last):
      ...
    AttributeError: module 'anyts.visualizers' has no attribute 'zipf_plot'
    ```
