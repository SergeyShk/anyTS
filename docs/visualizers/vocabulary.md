# Vocabulary growth and frequency spectrum

!!! info ""
    **anyts.visualizers.heaps_plot()**, **anyts.visualizers.frequency_spectrum_plot()**

## Description

Two plots of the distribution of the words of a text that complement [Zipf's law](zipf.md): the growth of the vocabulary with the length of the text by Heaps' law and the frequency spectrum - how many word types occur exactly once, twice, three times. The functions take the axes `ax` and return `Axes`.

## Heaps' law { #heaps_plot }

<!-- --8<-- [start:heaps_plot] -->
The size of the vocabulary $V$ after every word of the text and the fitted curve $V(N) = K \cdot N^{\beta}$ of `fit_heaps` with its parameters in the legend; the curve depends on the order of the words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text in order |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel`, `growth` (the curve), `fit` (a format string with `k` and `beta`) |
<!-- --8<-- [end:heaps_plot] -->

## Frequency spectrum { #frequency_spectrum_plot }

<!-- --8<-- [start:frequency_spectrum_plot] -->
The number of word types $V(m)$ that occur exactly $m$ times (`calc_frequency_spectrum`) in logarithmic coordinates; the left edge is the hapaxes. The spectrum underlies the measures of diversity of Yule, Sichel, Michéa and Honoré, and its shape shows how far the vocabulary of the text is from being exhausted.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |
<!-- --8<-- [end:frequency_spectrum_plot] -->

## Usage example

!!! example "Example"

    ``` python
    import matplotlib.pyplot as plt

    from anyts import WordsExtractor
    from anyts.visualizers import frequency_spectrum_plot, heaps_plot

    text = "The cat sat on the mat and the dog sat on the rug, and the cat saw the dog."
    words = WordsExtractor(lowercase=True).extract(text)
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 4.5))
    heaps_plot(words, ax=left)
    frequency_spectrum_plot(words, ax=right)
    ```
