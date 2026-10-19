# Lazy packages

!!! info ""
    **anyts.utils**

A package that imports its names on first use, so a light name does not load the dependencies of a heavy one.

## make_lazy

<!-- --8<-- [start:make_lazy] -->
`make_lazy(name, modules)` turns a package into a `LazyPackage`: every name of the mapping `modules` is imported from its module of the package when it is first read. Importing the package then loads only what it imports itself, so the highlighting does not load matplotlib and a module of statistics does not load spaCy with the components. A module of the package is also its attribute on first use, and a module named as one of its functions (*zipf*) leaves the function under that name. A package calls it at the end of its `__init__` with `__name__`; a `TYPE_CHECKING` block imports the same names for the type checkers. A name that is not a string or a mapping that is not one of strings to strings raises `SourceTypeError`; a name that is not that of an imported package, a lazy name that is not an identifier and a module that is not a dotted name of identifiers raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `name` | str | `-` | Name of the package, imported |
| `modules` | dict[str, str] | `-` | Module of the package by name |
<!-- --8<-- [end:make_lazy] -->

## LazyPackage

<!-- --8<-- [start:LazyPackage] -->
`LazyPackage` is the class of a package after `make_lazy`, a subclass of `types.ModuleType`. It imports a name of its mapping on first read and keeps it as its attribute, gives a module of the package as an attribute, and lists the names of the mapping in `dir()`. A name that is neither raises `AttributeError`, a module that fails to import for a missing dependency raises its `ModuleNotFoundError`, and an `AttributeError` raised while a module imports comes as an `ImportError` with it as the cause, since Python would take it for a missing name.
<!-- --8<-- [end:LazyPackage] -->

!!! example "Example"

    ``` python
    # The __init__ of a package
    from typing import TYPE_CHECKING

    from anyts.utils import make_lazy

    if TYPE_CHECKING:
        from .highlight import Highlight
        from .zipf import zipf

    __all__ = ["Highlight", "zipf"]

    make_lazy(__name__, {"Highlight": "highlight", "zipf": "zipf"})
    ```
