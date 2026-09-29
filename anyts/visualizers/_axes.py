from matplotlib.axes import Axes

from ..exceptions import ParameterError


def check_axes(ax: object) -> None:
    """
    Checking that the axes of a plot are a matplotlib Axes, if they are given

    Raises:
        ParameterError: If the axes are neither None nor an Axes
    """
    if ax is not None and not isinstance(ax, Axes):
        raise ParameterError(f"The axes must be a matplotlib Axes, not {type(ax).__name__}")
