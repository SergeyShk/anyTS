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

# Basic statistics: the least syllables of a complex word and letters of a long one (the
# bounds of Gunning's fog and of LIX), the characters counted as spaces
COMPLEX_SYL_FACTOR = 3
LONG_WORD_LETTER_FACTOR = 7
SPACES = (" ", "\t")
BASIC_STATS_DESC = {
    "n_sents": "Sentences",
    "n_words": "Words",
    "n_unique_words": "Unique words",
    "n_long_words": "Long words",
    "n_complex_words": "Complex words",
    "n_simple_words": "Simple words",
    "n_monosyllable_words": "Monosyllabic words",
    "n_polysyllable_words": "Polysyllabic words",
    "n_chars": "Characters",
    "n_letters": "Letters",
    "n_spaces": "Spaces",
    "n_syllables": "Syllables",
    "n_punctuations": "Punctuation marks",
}
PUNCTUATION_TYPES = {
    "comma": "Commas",
    "period": "Periods",
    "question": "Question marks",
    "exclamation": "Exclamation marks",
    "ellipsis": "Ellipses",
    "colon": "Colons",
    "semicolon": "Semicolons",
    "dash": "Dashes",
    "hyphen": "Hyphens",
    "angle_quotes": "Guillemets",
    "straight_quotes": "Straight and curly quotes",
    "parentheses": "Parentheses",
    "other": "Other marks",
}

# Readability statistics: the least syllables of a polysyllabic word of SMOG and Gunning's
# fog and letters of a long word of LIX and RIX
SMOG_COMPLEX_SYL_FACTOR = 3
LIX_LONG_WORD_LETTER_FACTOR = 7
READABILITY_STATS_DESC = {
    "flesch_reading_easy": "Flesch reading ease",
    "flesch_kincaid_grade": "Flesch-Kincaid grade",
    "coleman_liau_index": "Coleman-Liau index",
    "automated_readability_index": "Automated readability index",
    "smog_index": "SMOG index",
    "gunning_fog_index": "Gunning fog index",
    "lix": "LIX readability index",
    "rix": "RIX readability index",
    "mu_index": "Legibilidad µ",
    "consensus_grade": "Consensus grade",
    "reading_time": "Reading time (min)",
}
READABILITY_GRADE_STATS = (
    "flesch_kincaid_grade",
    "coleman_liau_index",
    "automated_readability_index",
    "smog_index",
    "gunning_fog_index",
)
# Coefficients of the formulas fitted on English: Flesch (1948), Kincaid et al. (1975),
# Coleman and Liau (1975), Smith and Senter (1967), McLaughlin (1969), Gunning (1952)
READABILITY_PRESETS: dict[str, dict[str, tuple[float, ...]]] = {
    "original": {
        "flesch_reading_easy": (1.015, 84.6, 206.835),
        "flesch_kincaid_grade": (0.39, 11.8, 15.59),
        "coleman_liau_index": (0.0588, 0.296, 15.8),
        "automated_readability_index": (4.71, 0.5, 21.43),
        "smog_index": (1.043, 30, 3.1291),
        "gunning_fog_index": (0.4,),
    }
}
# Lower bounds of the Flesch reading ease and the years of schooling they give, as
# text_standard of textstat reads the table of Flesch (1948); below the last bound - 13
READING_EASE_GRADES: tuple[tuple[float, float], ...] = (
    (90, 5),
    (80, 6),
    (70, 7),
    (60, 8.5),
    (50, 10),
    (40, 11),
    (30, 12),
)
# Scales of describe_level: lower bounds in descending order, the lowest band open below.
# The reading ease by the school levels of Flesch (How to Write Plain English, 1979)
READING_EASE_LEVELS: tuple[tuple[float, str], ...] = (
    (90, "5th grade"),
    (80, "6th grade"),
    (70, "7th grade"),
    (60, "8th and 9th grade"),
    (50, "10th to 12th grade"),
    (30, "college"),
    (10, "college graduate"),
    (0, "professional"),
)
# LIX by the text types of Björnsson (1968)
LIX_LEVELS: tuple[tuple[float, str], ...] = (
    (60, "very hard texts, laws and bureaucratic language"),
    (50, "hard texts, popular science, official texts"),
    (40, "texts of medium difficulty, magazine articles"),
    (30, "easy texts, fiction, newspaper articles"),
    (0, "very easy texts, children's books"),
)
# RIX as years of schooling by Anderson (1983), college as 13
RIX_GRADES: tuple[tuple[float, float], ...] = (
    (7.2, 13),
    (6.2, 12),
    (5.3, 11),
    (4.5, 10),
    (3.7, 9),
    (3.0, 8),
    (2.4, 7),
    (1.8, 6),
    (1.3, 5),
    (0.8, 4),
    (0.5, 3),
    (0.2, 2),
    (0, 1),
)
# Years of schooling of the school stages of the United States and the age of the reader
GRADE_AGE_LEVELS: tuple[tuple[int, int, str, str], ...] = (
    (1, 5, "elementary school, grades 1-5", "6-11 years"),
    (6, 8, "middle school, grades 6-8", "11-14 years"),
    (9, 12, "high school, grades 9-12", "14-18 years"),
    (13, 16, "college", "18-22 years"),
)
POSTGRADUATE_LEVEL = ("graduate school", "over 22 years")
# Silent reading speed of adults in English, words per minute, and the speeds (aloud,
# silent) of the norms: Brysbaert (2019)
READING_SPEED_WPM = 238
READING_SPEED_NORMS: dict[str, tuple[int, ...]] = {"adult": (183, 238)}
