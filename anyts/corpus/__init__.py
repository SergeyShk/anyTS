from typing import TYPE_CHECKING

from .._lazy import make_lazy

if TYPE_CHECKING:
    from .collocations import Collocation, collocations
    from .compare import (
        COMPARISON_COLUMNS,
        bootstrap_median_diff,
        calc_cliff_delta,
        calc_cohen_d,
        check_comparison_params,
        compare_features,
        compare_values,
        holm_correction,
    )
    from .dispersion import Dispersion, dispersion
    from .keyness import FrequencyReference, Keyword, check_keyness_params, keyness
    from .kwic import Concordance, format_kwic, kwic, print_kwic
    from .stylometry import (
        ZetaScore,
        delta,
        delta_profiles,
        frequency_table,
        kilgarriff_chi2,
        mendenhall_curve,
        mendenhall_distance,
        z_scores,
        zeta,
    )

# The module of every name, imported on first use: the concordance does not load pandas
_MODULES = {
    "COMPARISON_COLUMNS": "compare",
    "Collocation": "collocations",
    "Concordance": "kwic",
    "Dispersion": "dispersion",
    "FrequencyReference": "keyness",
    "Keyword": "keyness",
    "ZetaScore": "stylometry",
    "bootstrap_median_diff": "compare",
    "calc_cliff_delta": "compare",
    "calc_cohen_d": "compare",
    "check_comparison_params": "compare",
    "check_keyness_params": "keyness",
    "collocations": "collocations",
    "compare_features": "compare",
    "compare_values": "compare",
    "delta": "stylometry",
    "delta_profiles": "stylometry",
    "dispersion": "dispersion",
    "format_kwic": "kwic",
    "frequency_table": "stylometry",
    "holm_correction": "compare",
    "keyness": "keyness",
    "kilgarriff_chi2": "stylometry",
    "kwic": "kwic",
    "mendenhall_curve": "stylometry",
    "mendenhall_distance": "stylometry",
    "print_kwic": "kwic",
    "z_scores": "stylometry",
    "zeta": "stylometry",
}

__all__ = [
    "COMPARISON_COLUMNS",
    "Collocation",
    "Concordance",
    "Dispersion",
    "FrequencyReference",
    "Keyword",
    "ZetaScore",
    "bootstrap_median_diff",
    "calc_cliff_delta",
    "calc_cohen_d",
    "check_comparison_params",
    "check_keyness_params",
    "collocations",
    "compare_features",
    "compare_values",
    "delta",
    "delta_profiles",
    "dispersion",
    "format_kwic",
    "frequency_table",
    "holm_correction",
    "keyness",
    "kilgarriff_chi2",
    "kwic",
    "mendenhall_curve",
    "mendenhall_distance",
    "print_kwic",
    "z_scores",
    "zeta",
]

make_lazy(__name__)
