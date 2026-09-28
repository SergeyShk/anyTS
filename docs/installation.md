# Installation

## Requirements

*   `python` 3.11 or newer
*   `spaCy` 3.7 or newer
*   `numpy`, `scipy`, `pandas`
*   `matplotlib`, `graphviz` - for the visualizers

The dependencies are installed with the package. Rendering the word tree and the network of collocations also needs the executables of [Graphviz](https://graphviz.org/download/), installed with the package manager of the system. A language library built on anyTS installs it as its own dependency.

## From PyPI

``` bash
pip install anyts
```

## From the repository

``` bash
git clone https://github.com/SergeyShk/anyTS.git
cd anyTS
uv sync --all-groups
```
