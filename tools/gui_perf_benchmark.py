#!/usr/bin/env python3
import os
import time
import tempfile
import numpy as np
import pandas as pd


def bench(fn, repeat=5):
    vals = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        vals.append(time.perf_counter() - t0)
    return min(vals)


def main():
    np.random.seed(0)
    arr = np.random.randn(1024, 512)

    # 1) CSV load path: default pandas vs tuned flags used in app_qt
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "dense.csv")
        np.savetxt(p, arr, delimiter=",")
        t_csv_old = bench(lambda: pd.read_csv(p, header=None).values, repeat=3)
        t_csv_new = bench(lambda: pd.read_csv(p, header=None, na_filter=False, low_memory=False).values, repeat=3)

    # 2) Plot refresh storm: old immediate redraw N times vs new debounce (1 redraw)
    def heavy_plot_step(x):
        # simulate imshow+stats path cost
        _ = np.nan_to_num(x)
        _ = np.percentile(x, [1, 99])

    t_plot_old = bench(lambda: [heavy_plot_step(arr) for _ in range(20)], repeat=3)
    t_plot_new = bench(lambda: [heavy_plot_step(arr) for _ in range(1)], repeat=3)

    # 3) Batch core IO path: old (module writes final + GUI re-saves) vs new (temp write + single final save)
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "a.csv")
        f2 = os.path.join(td, "b.csv")
        f3 = os.path.join(td, "c.csv")

        def old_io():
            np.savetxt(f1, arr, delimiter=",")  # core out
            _ = pd.read_csv(f1, header=None, na_filter=False, low_memory=False).values
            np.savetxt(f2, arr, delimiter=",")  # GUI _save_outputs re-save

        def new_io():
            np.savetxt(f1, arr, delimiter=",")  # temp core out
            _ = pd.read_csv(f1, header=None, na_filter=False, low_memory=False).values
            np.savetxt(f3, arr, delimiter=",")  # single final save

        # Add one more extra write to old to represent redundant png generation path in previous flow
        def old_io_with_redundancy():
            old_io()
            np.savetxt(f3, arr[:64, :64], delimiter=",")

        t_io_old = bench(old_io_with_redundancy, repeat=3)
        t_io_new = bench(new_io, repeat=3)

    print("GUI Performance Micro-benchmark")
    print(f"1) CSV读取: old={t_csv_old:.4f}s, new={t_csv_new:.4f}s, speedup={t_csv_old / max(t_csv_new,1e-9):.2f}x")
    print(f"2) 绘图刷新风暴(20次触发): old={t_plot_old:.4f}s, new={t_plot_new:.4f}s, speedup={t_plot_old / max(t_plot_new,1e-9):.2f}x")
    print(f"3) 批处理核心I/O: old={t_io_old:.4f}s, new={t_io_new:.4f}s, speedup={t_io_old / max(t_io_new,1e-9):.2f}x")


if __name__ == '__main__':
    main()
