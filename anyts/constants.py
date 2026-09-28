# Lexical diversity: the conventions of koRpus and lexical-diversity
MATTR_WINDOW_LEN = 50
MTLD_TTR_THRESHOLD = 0.72
MTLD_MIN_LEN = 10
# Block of factor starts and window of offsets in the MA-MTLD and MTLD-W computation
MTLD_BLOCK_SIZE = 4096
MTLD_WINDOW_LEN = 32
HDD_SAMPLE_SIZE = 42
DIVERSITY_LOG_BASE = 10
BRUNET_W_EXPONENT = 0.172
DIVERSITY_STATS_DESC = {
    "ttr": "Type-Token Ratio (TTR)",
    "rttr": "Root Type-Token Ratio (RTTR)",
    "cttr": "Corrected Type-Token Ratio (CTTR)",
    "httr": "Herdan Type-Token Ratio (HTTR)",
    "sttr": "Summer Type-Token Ratio (STTR)",
    "mttr": "Maas Type-Token Ratio (MTTR)",
    "dttr": "Dugast Type-Token Ratio (DTTR)",
    "mattr": "Moving Average Type-Token Ratio (MATTR)",
    "msttr": "Mean Segmental Type-Token Ratio (MSTTR)",
    "mtld": "Measure of Textual Lexical Diversity (MTLD)",
    "mamtld": "Moving Average Measure of Textual Lexical Diversity (MA-MTLD)",
    "mtldw": "Moving Average Measure of Textual Lexical Diversity with Wrap (MTLD-W)",
    "hdd": "Hypergeometric Distribution D (HD-D)",
    "simpson_index": "Simpson's index (D)",
    "inverse_simpson_index": "Inverse Simpson's index (1/D)",
    "gini_simpson_index": "Gini-Simpson index (1-D)",
    "hapax_index": "Hapax index (Honoré's R)",
    "yule_k": "Yule's characteristic K",
    "yule_i": "Yule's inverse characteristic I",
    "herdan_vm": "Herdan's Vm",
    "sichel_s": "Sichel's S",
    "michea_m": "Michéa's M",
    "brunet_w": "Brunet's W",
    "dugast_k": "Dugast's k",
    "baayen_p": "Baayen's P",
    "hapax_ratio": "Hapax ratio",
    "alpha2": "Exponent α₂",
    "entropy": "Shannon entropy (bits)",
    "evenness": "Evenness",
    "perplexity": "Perplexity",
    "zipf_alpha": "Zipf's law slope (α)",
    "heaps_beta": "Heaps' law exponent (β)",
}

# Relations that are not arguments of a word: coordination, parataxis, punctuation
VALENCY_IGNORED_DEPS = frozenset({"cc", "conj", "parataxis", "punct"})

# Measures of keyness, of association of collocations, of dispersion of words and of stylometry
KEYNESS_MEASURES = {
    "log_likelihood": "Log-likelihood G²",
    "chi2": "Chi-square with Yates's correction",
    "diff": "Difference of normalized frequencies %DIFF",
    "log_ratio": "Binary logarithm of the ratio of normalized frequencies",
    "bic": "Bayesian information criterion",
    "ell": "Effect size for the log-likelihood",
    "odds_ratio": "Odds ratio",
}
# Critical values of G² with one degree of freedom, by the level of significance
G2_CRITICAL_VALUES = {0.05: 3.84, 0.01: 6.63, 0.001: 10.83, 0.0001: 15.13}
COLLOCATION_MEASURES = {
    "mi": "Mutual information MI",
    "mi3": "Cubic mutual information MI³",
    "t_score": "t-score",
    "dice": "Dice coefficient",
    "logdice": "logDice",
    "log_likelihood": "Log-likelihood G²",
    "npmi": "Normalized pointwise mutual information",
    "min_sensitivity": "Minimum sensitivity",
}
DISPERSION_STATS_DESC = {
    "dp": "Deviation of proportions DP of Gries",
    "dp_norm": "Normalized DP",
    "juilland_d": "Juilland's D",
    "carroll_d2": "Carroll's D2",
    "rosengren_s": "Rosengren's S",
    "kl_divergence": "Kullback-Leibler divergence",
}
DELTA_VARIANTS = {
    "burrows": "Burrows's Delta - Manhattan distance of the z-scores divided by the number of units",
    "quadratic": "Argamon's quadratic Delta - Euclidean distance of the z-scores divided by the number of units",
    "eder": "Eder's Delta - Manhattan distance of the z-scores weighted by rank",
    "cosine": "Cosine Delta - cosine distance of the z-scores",
}

# Labels of the plots by the name of the visualizer; the labels with fields in braces are
# format strings, and a language library passes its own labels over these
VISUALIZER_LABELS = {
    "zipf": {
        "title": "Zipf's law",
        "xlabel": "Rank of the word",
        "ylabel": "Frequency of the word",
        "experimental": "Experimental law",
        "theoretical": "Theoretical law",
        "fit": "Zipf-Mandelbrot: q={q:.2f}, s={s:.2f}",
    },
    "zipf_theory": {"theoretical": "Theoretical law"},
    "heaps_plot": {
        "title": "Heaps' law",
        "xlabel": "Length of the text, words",
        "ylabel": "Size of the vocabulary",
        "growth": "Vocabulary growth",
        "fit": "K·N^β: K={k:.2f}, β={beta:.2f}",
    },
    "frequency_spectrum_plot": {
        "title": "Frequency spectrum",
        "xlabel": "Frequency of a word type m",
        "ylabel": "Number of word types V(m)",
    },
    "sentence_lengths_plot": {
        "title": "Sentence lengths",
        "xlabel": "Number of the sentence",
        "ylabel": "Words in the sentence",
        "length": "Sentence length",
        "average": "Moving average ({window})",
        "distribution": "Distribution",
    },
    "fingerprinting": {"title": "Literature fingerprinting"},
    "dispersion_plot": {
        "title": "Lexical dispersion",
        "xlabel": "Position of the word in the text",
    },
    "keyness_plot": {
        "title": "Keywords",
        "xlabel": "|{field}|",
        "xlabel_log": "|log2({field})|",
        "target": "target corpus",
        "reference": "reference corpus",
    },
    "dendrogram_plot": {"title": "Clustering of the texts", "xlabel": "Distance"},
    "pca_plot": {
        "title": "Principal components",
        "xlabel": "Component 1 ({share:.1%})",
        "ylabel": "Component 2 ({share:.1%})",
    },
    "mds_plot": {
        "title": "Multidimensional scaling",
        "xlabel": "Dimension 1",
        "ylabel": "Dimension 2",
    },
    "mendenhall_plot": {
        "title": "Mendenhall curves",
        "xlabel": "Length of the word, characters",
        "ylabel": "Share of the words",
    },
}
