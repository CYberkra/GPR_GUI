import os
from pathlib import Path

import numpy as np
from scipy.io import savemat


def shot2RecTime1(travelTime, ixs, ixr, dt, nx):
    if nx < travelTime.shape[1]:
        it = np.round(travelTime[:, :ixs] / dt).astype(int) + 1 + np.round(travelTime[:, :ixs] / dt).astype(int) + 1
    else:
        it = np.round(travelTime / dt).astype(int) + 1 + np.round(travelTime / dt).astype(int) + 1
    return it


def migrate(travelTime, xRecGrid, xShotAndRecGrid, shot, dt, nz, nx, ixs, out_dir=None):
    m = np.zeros((nz, nx))
    xRecGrid = np.atleast_1d(xRecGrid)
    for ixr in range(len(xRecGrid)):
        xr = xRecGrid[ixr]
        matches = np.where(np.atleast_1d(xShotAndRecGrid) == np.atleast_1d(xr))[0]
        if len(matches) == 0:
            continue
        idxXRec = matches[0]
        it = shot2RecTime1(travelTime, ixs - 1, idxXRec, dt, nx)

        max_it = np.max(it)
        if max_it >= shot.shape[0]:
            pad_rows = max_it - shot.shape[0] + 1
            padded_shot = np.pad(shot, ((0, pad_rows), (0, 0)), mode="constant")
        else:
            padded_shot = shot

        migrated_values = padded_shot[it, ixs - 1]
        m = np.reshape(migrated_values, (nz, nx))

    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        savemat(out / f"result_{ixs}.mat", {"im1": m.copy()})
    return m


def process_kir(data: np.ndarray, dx=0.05, dt=0.1, v=0.1, aperture=20, **kwargs):
    """Legacy Kir minimal path: vectorized Kirchhoff-like migration."""
    arr = np.array(data, dtype=float, copy=True)
    ny, nx = arr.shape
    migrated = np.zeros_like(arr)

    t = np.arange(ny) * dt
    if ny > 0:
        t[0] = 1e-6
    t0_sq = t ** 2

    for ix in range(nx):
        start_tr = max(0, ix - int(aperture))
        end_tr = min(nx, ix + int(aperture) + 1)
        dist = (np.arange(start_tr, end_tr) - ix) * dx
        dx_term = 4 * (dist ** 2) / max(v ** 2, 1e-12)
        t_travel = np.sqrt(t0_sq[:, None] + dx_term[None, :])
        t_pos = t_travel / max(dt, 1e-12)

        for i_d, tr in enumerate(range(start_tr, end_tr)):
            row_ids = np.arange(ny)
            pos = t_pos[row_ids, i_d]
            valid = (pos >= 0.0) & (pos < (ny - 1))
            if not np.any(valid):
                continue
            rows = row_ids[valid]
            pos_v = pos[valid]
            i0 = np.floor(pos_v).astype(int)
            frac = pos_v - i0
            i1 = np.minimum(i0 + 1, ny - 1)
            sampled = (1.0 - frac) * arr[i0, tr] + frac * arr[i1, tr]
            migrated[rows, ix] += sampled

    return migrated
