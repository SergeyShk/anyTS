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
