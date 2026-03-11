import numpy as np

try:
    import cupy as cp  # noqa: F401
    from numba import cuda  # noqa: F401
except Exception:  # pragma: no cover
    cp = None
    cuda = None


def rtm_gpu(*args, **kwargs):
    """Legacy RTM GPU entry adapted from inbound script.

    TODO: wire full FDTD dependency chain (gridinterp/padgrid/updatafwd/updatabwd).
    """
    if cp is None or cuda is None:
        raise RuntimeError("RTM GPU dependencies unavailable: require cupy + numba[cuda]")
    raise NotImplementedError("Legacy RTM GPU pipeline integration TODO")
