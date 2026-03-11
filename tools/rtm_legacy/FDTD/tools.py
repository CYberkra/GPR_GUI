import os
import glob
import shutil
from scipy.ndimage import gaussian_filter1d, median_filter, binary_closing
import pandas as pd
from scipy.io import loadmat
import numpy as np
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.backends.backend_tkagg
from scipy.interpolate import UnivariateSpline
import re
from scipy.ndimage import laplace
from pathlib import Path
from typing import Tuple, Dict, Union, Optional
from scipy.sparse import spdiags
mpl.use('TkAgg')
def read_param(fname, param_name):
    try:
        with open(fname, 'r') as file:
            for line in file:
                line = line.strip()  # 去除行首尾空白
                if line.startswith(param_name):
                    parts = line.split()  # 使用空格分割字符串
                    if len(parts) < 2:
                        raise ValueError(f'Invalid line format for parameter {param_name} in file: {fname}')

                    # 尝试将参数值转换为数值类型
                    try:
                        return float(parts[1])
                    except ValueError:
                        return parts[1]  # 保持字符串格式

            # 如果遍历完文件还没有找到参数，抛出错误
            raise ValueError(f'Parameter {param_name} not found in file: {fname}')
    except FileNotFoundError:
        raise FileNotFoundError(f'Cannot open file: {fname}')




def read_gpr_csv_arrays(csv_path: Union[str, Path],
                        reshape_as: str = "time_rows",
                        verify_samples: Optional[int] = None
                        ) -> Tuple[np.ndarray, np.ndarray,
                                   np.ndarray, np.ndarray,
                                   np.ndarray, Dict[str, float]]:
    """
    Read an airborne‑GPR CSV (4‑line header + data.csv) and return:

    1) gpr_mat : 2‑D NumPy array of radar amplitudes
    2) lon     : 1‑D NumPy array (per trace)
    3) lat     : 1‑D NumPy array (per trace)
    4) elev    : 1‑D NumPy array (per trace, ground elevation in m)
    5) flight  : 1‑D NumPy array (per trace, flight height in m)
    6) meta    : dict with header information

    Parameters
    ----------
    csv_path      : str | Path
    reshape_as    : "time_rows" (default) ➜ matrix shape = (n_samples, n_traces)
                    "trace_rows"          ➜ matrix shape = (n_traces, n_samples)
    verify_samples: if set, raise error when Number of Samples mismatches.
    """
    csv_path = Path(csv_path)

    # ---------- 1) Parse 4‑line header ----------
    with csv_path.open(encoding="utf-8") as f:
        hdr = [next(f).strip() for _ in range(4)]

    _val = lambda s: s.split("=", 1)[1].split(",")[0].strip()

    meta = {
        "n_samples":        int(_val(hdr[0])),
        "time_window_ns":   float(_val(hdr[1])),
        "n_traces":         int(_val(hdr[2])),
        "trace_interval_m": float(_val(hdr[3])),
    }
    if verify_samples is not None and meta["n_samples"] != verify_samples:
        raise ValueError(f'Number of Samples = {meta["n_samples"]}, '
                         f"expected {verify_samples}")

    # ---------- 2) Read data.csv section ----------
    df = pd.read_csv(csv_path, skiprows=4, header=None,
                     names=["lon", "lat", "elev", "gpr", "flight"])

    # ---------- 3) Per‑trace geographic attributes ----------
    # 每 n_samples 行对应 1 条道，取第一行即可
    per_trace = df.groupby(df.index // meta["n_samples"]).first()
    lon    = per_trace["lon"].to_numpy()
    lat    = per_trace["lat"].to_numpy()
    elev   = per_trace["elev"].to_numpy()
    flight = per_trace["flight"].to_numpy()

    # ---------- 4) Reshape radar column ----------
    gpr_1d   = df["gpr"].to_numpy()
    expected = meta["n_samples"] * meta["n_traces"]
    if gpr_1d.size != expected:
        raise ValueError(f"Data length {gpr_1d.size} != {expected}")

    gpr_mat = gpr_1d.reshape((meta["n_traces"], meta["n_samples"]))
    if reshape_as == "time_rows":
        gpr_mat = gpr_mat.T      # (n_samples, n_traces)
    elif reshape_as != "trace_rows":
        raise ValueError('reshape_as must be "time_rows" or "trace_rows"')

    return gpr_mat, lon, lat, elev, flight, meta
def load_csv_file(directory, target_file_name,
                  delimiter=None,  # None -> auto detect
                  has_header=True,
                  dtype=None,
                  encoding=None):
    import os, pandas as pd
    file_path = os.path.join(directory, target_file_name)
    if not os.path.isfile(file_path):
        print("Target .csv file not found.")
        return None

    # Auto encodings
    encs = [encoding] if encoding else ['utf-8', 'utf-8-sig', 'utf-16', 'gbk', 'latin1']
    header = 0 if has_header else None
    for enc in encs:
        try:
            df = pd.read_csv(file_path,
                             sep=delimiter,  # None -> auto
                             engine='python',
                             header=header,
                             dtype=dtype,
                             encoding=enc,
                             on_bad_lines='skip')
            print(f"Loaded data.csv from {file_path} (enc='{enc}', sep='{delimiter}')")
            return {'data.csv': df.to_numpy(),
                    'columns': list(df.columns) if has_header else None}
        except Exception as e:
            last_err = e
    print("Failed:", last_err)
    return None

def load_mat_file(directory, target_file_name='data.csv.mat'):
    """
    在指定目录中查找并加载特定的.mat文件，并返回不包含头部信息的实际数据。

    Args:
    directory (str): 查找.mat文件的目录路径。
    target_file_name (str): 要加载的特定文件名称，默认为'data.csv.mat'。

    Returns:
    dict or None: 如果找到文件，则返回仅包含实际数据的字典；否则返回None。
    """
    # 构建搜索路径
    search_pattern = os.path.join(directory, '*.mat')
    # 搜索所有.mat文件
    mat_files = glob.glob(search_pattern)

    for file_path in mat_files:
        # 检查文件名是否是目标文件
        if os.path.basename(file_path) == target_file_name:
            # 加载.mat文件
            data = loadmat(file_path)
            print(f"Loaded data.csv from {file_path}")

            # 移除.mat文件中的元数据，只保留实际数据
            data_cleaned = {key: value for key, value in data.items() if not key.startswith('__')}
            return data_cleaned

    print("Target .mat file not found.")
    return None


def setup(len, depth, freq, T,num_cal):
    # 常数
    c = 3e8
    # 初始的25值
    factor = 60
    # 计算距离
    distance = 2 * depth

    # 计算dx, dz, dt
    dx = c / (factor * freq)
    dz = dx
    dt = dx / (2 * c)  # 时间步长

    # 计算ntmartix
    ntmartix = math.ceil(T / (dt * 1e9))

    # 计算nxmartix和nzmartix
    nzmartix = math.ceil(depth / dx)
    nxmartix = 2 * nzmartix

    nx = math.ceil(len / dx)
    # 调整factor以确保nxmartix是100的倍数
    while nx % num_cal != 0:
        factor += 1
        dx = c / (factor * freq)
        dz = dx
        dt = dx / (2 * c)  # 时间步长
        ntmartix = math.ceil(T / (dt * 1e9))
        nzmartix = math.ceil(depth / dx)
        nxmartix = 2 * nzmartix
        nx = math.ceil(len / dx)
    # Get the current folder path
    current_folder = os.getcwd()

    # Define the full paths for image3 and image4 folders within the tools folder
    tools_folder = current_folder
    folder1 = os.path.join(tools_folder, 'tools', 'image3')
    folder2 = os.path.join(tools_folder, 'tools', 'image4')

    # Check and create image3 folder
    if not os.path.exists(folder1):
        os.makedirs(folder1)

    # Check and create image4 folder
    if not os.path.exists(folder2):
        os.makedirs(folder2)

    # Clear the contents of folder1 and folder2
    clearmat(folder1)
    clearmat(folder2)

    return factor, nxmartix, ntmartix, nzmartix, dx, dt

def setup_ini(len, depth, freq, T,num_cal):
    # 常数
    c = 3e8
    # 初始的25值
    factor = 60
    # 计算距离
    distance = 2 * depth

    # 计算dx, dz, dt
    dx = c / (factor * freq)
    dz = dx
    dt = dx / (2 * c)  # 时间步长

    # 计算ntmartix
    ntmartix = math.ceil(T / (dt * 1e9))

    # 计算nxmartix和nzmartix
    nzmartix = math.ceil(depth / dx)
    nxmartix = math.ceil(len / dx)

    nx = math.ceil(len / dx)
    # 调整factor以确保nxmartix是100的倍数
    while nx % num_cal != 0:
        factor += 1
        dx = c / (factor * freq)
        dz = dx
        dt = dx / (2 * c)  # 时间步长
        ntmartix = math.ceil(T / (dt * 1e9))
        nzmartix = math.ceil(depth / dx)
        nxmartix  = math.ceil(len / dx)
    # Get the current folder path
    current_folder = os.getcwd()

    # Define the full paths for image3 and image4 folders within the tools folder
    tools_folder = current_folder
    folder1 = os.path.join(tools_folder, 'tools', 'image3')
    folder2 = os.path.join(tools_folder, 'tools', 'image4')

    # Check and create image3 folder
    if not os.path.exists(folder1):
        os.makedirs(folder1)

    # Check and create image4 folder
    if not os.path.exists(folder2):
        os.makedirs(folder2)

    # Clear the contents of folder1 and folder2
    clearmat(folder1)
    clearmat(folder2)

    return factor, nxmartix, ntmartix, nzmartix, dx, dt

# 获取当前文件夹路径
current_folder = os.getcwd()

# 定义在tools文件夹内的image3和image4文件夹的完整路径
tools_folder =current_folder
folder1 = os.path.join(tools_folder, 'tools', 'image3')
folder2 = os.path.join(tools_folder, 'tools', 'image4')

# 检查并创建image3文件夹
if not os.path.exists(folder1):
    os.makedirs(folder1)

# 检查并创建image4文件夹
if not os.path.exists(folder2):
    os.makedirs(folder2)


def clearmat(folder_path):
    """清除文件夹中的所有文件"""
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


# 清除image3和image4文件夹中的.mat文件
#clearmat(folder1)
#clearmat(folder2)


def set_source(fr, t, signal_type):
    """
    根据指定的时间向量和主要频率生成信号。
    支持 'black'（黑曼-哈里斯窗脉冲）和 'ricker'（里克波）两种信号类型。

    参数:
        fr (float): 主要频率 (Hz)
        t (numpy.ndarray): 时间向量 (s)
        signal_type (str): 信号类型，可以是 'black' 或 'ricker'

    返回:
        numpy.ndarray: 生成的信号
    """
    if signal_type == "black":
        # 初始化黑曼-哈里斯窗的系数和周期
        a = np.array([0.35322222, -0.488, 0.145, -0.010222222])
        T = 1.14 / fr
        window = np.zeros_like(t)

        # 计算黑曼-哈里斯窗函数
        for n in range(4):
            window += a[n] * np.cos(2 * n * np.pi * t / T)

        # 窗函数外的时间置零
        window[t >= T] = 0

        # 计算窗函数的导数并归一化
        p = np.diff(window, append=0)
        p = p / np.max(np.abs(p))

    elif signal_type == "ricker":
        # 里克波的中心时间
        t0 = 1 / fr
        tau = t - t0

        # 生成里克波
        p = (1 - (tau ** 2) * (fr ** 2) * (np.pi ** 2)) * np.exp(-(tau ** 2) * (np.pi ** 2) * (fr ** 2))

    return p

import numpy as np
import numpy as np

import numpy as np

def Fstar(sz, sx):
    sz2 = 2 * sz - 1
    sx2 = 2 * sx - 1
    sz1 = sz2 - 1
    sx1 = sx2 - 1
    nrow = sz2 * sx2
    ncol = sz1 * sx1
    A = np.zeros((nrow, ncol))
    nray = 0
    rayxz = np.zeros((2, 1000))
    temp = np.zeros((2, 1000))

    for kz in range(1, sz2 + 1):
        z0 = kz - 1
        for kx in range(1, sx2 + 1):
            x0 = kx - 1
            nray += 1
            dxx = sx - kx
            dzz = sz - kz

            if dxx == 0 or dzz == 0:
                if dxx == 0 and dzz != 0:
                    np_val = 0
                    if dzz > 0:
                        for kk in range(kz, sz + 1):
                            np_val += 1
                            temp[0, np_val - 1] = x0
                            temp[1, np_val - 1] = kk - 1
                    else:
                        for kk in range(kz, sz - 1, -1):
                            np_val += 1
                            temp[0, np_val - 1] = x0
                            temp[1, np_val - 1] = kk - 1
                else:
                    np_val = 0
                    if dxx > 0:
                        for kk in range(kx, sx + 1):
                            np_val += 1
                            temp[0, np_val - 1] = kk - 1
                            temp[1, np_val - 1] = z0
                    else:
                        for kk in range(kx, sx - 1, -1):
                            np_val += 1
                            temp[0, np_val - 1] = kk - 1
                            temp[1, np_val - 1] = z0
            else:
                slop = dzz / dxx
                rslop = 1.0 / slop
                seg = 1
                rayxz[:, 0] = [x0, z0]

                if slop > 0:
                    if dxx > 0:  # I
                        x = x0
                        for ix in range(kx + 1, sx + 1):
                            seg += 1
                            x += 1
                            z = slop * (x - x0)
                            rayxz[:, seg - 1] = [x, z + z0]

                        z = z0
                        for iz in range(kz + 1, sz + 1):
                            seg += 1
                            z += 1
                            x = (z - z0) * rslop
                            rayxz[:, seg - 1] = [x + x0, z]
                    else:  # IV
                        x = x0
                        for ix in range(kx - 1, sx - 1, -1):
                            seg += 1
                            x -= 1
                            z = slop * (x - x0)
                            rayxz[:, seg - 1] = [x, z + z0]

                        z = z0
                        for iz in range(kz - 1, sz - 1, -1):
                            seg += 1
                            z -= 1
                            x = (z - z0) * rslop
                            rayxz[:, seg - 1] = [x + x0, z]
                else:
                    if dxx < 0:  # II
                        x = x0
                        for ix in range(kx - 1, sx - 1, -1):
                            seg += 1
                            x -= 1
                            z = slop * (x - x0)
                            rayxz[:, seg - 1] = [x, z + z0]

                        z = z0
                        for iz in range(kz + 1, sz + 1):
                            seg += 1
                            z += 1
                            x = (z - z0) * rslop
                            rayxz[:, seg - 1] = [x + x0, z]
                    else:  # III
                        x = x0
                        for ix in range(kx + 1, sx + 1):
                            seg += 1
                            x += 1
                            z = slop * (x - x0)
                            rayxz[:, seg - 1] = [x, z + z0]

                        z = z0
                        for iz in range(kz - 1, sz - 1, -1):
                            seg += 1
                            z -= 1
                            x = (z - z0) * rslop
                            rayxz[:, seg - 1] = [x + x0, z]

                # Sorting
                sorted_indices = np.argsort(rayxz[0, :seg])
                rayxz[:, :seg] = rayxz[:, sorted_indices]
                temp[:, 0] = rayxz[:, 0]
                np_val = 1

                for k in range(1, seg):
                    dist = np.linalg.norm(rayxz[:, k] - rayxz[:, k - 1])
                    if dist > 1.e-5:
                        np_val += 1
                        temp[:, np_val - 1] = rayxz[:, k]

            for k in range(1, np_val):
                dist = np.linalg.norm(temp[:, k] - temp[:, k - 1])
                aa = 0.5 * (temp[:, k] + temp[:, k - 1])
                indx = int(np.floor(aa[0]))
                indz = int(np.floor(aa[1]))
                ind = indz * sx1 + indx
                A[nray - 1, ind] = dist

    return A


def Time2d(S, Shot, dx, nz, nx, Fs_z, Fs_x, Fs):
    T0 = 1.e8
    Fs_z2 = 2 * Fs_z - 1
    Fs_x2 = 2 * Fs_x - 1
    zs = Shot[0] + Fs_z - 1
    xs = Shot[1] + Fs_x - 1
    mxV = np.max(S)
    T = np.ones((nz + Fs_z2, nx + Fs_x2)) * T0
    M = np.copy(T)

    M[Fs_z-1:nz + Fs_z, Fs_x-1:nx + Fs_x] = 0
    iz = np.arange(Fs_z, nz + Fs_z)
    ix = np.arange(Fs_x, nx + Fs_x)
    T[zs-1, xs] = 0
    M[zs-1, xs] = T0

    z1 = np.arange(-Fs_z + 1, Fs_z)
    z2 = np.arange(-Fs_z + 1, Fs_z - 1)
    z3 = z1 + zs
    x1 = np.arange(-Fs_x + 1, Fs_x)
    x2 = np.arange(-Fs_x + 1, Fs_x - 1)
    x3 = x1 + xs
    AS = S[np.ix_(z2 + zs-1, x2 + xs)]
    TT = T[np.ix_(z3-1, x3)]
    # 将 AS 展平并乘以 Fs，然后加上 T(zs, xs)
    # 展平 AS 为 (121,)
    AS_flat = AS.flatten()
    # 将 AS_flat 转换为 (121, 1) 的二维数组，以便与 Fs 进行广播操作
    AS_flat_reshaped = AS_flat[:, np.newaxis]
    # 进行元素级乘法操作，结果将是 (121, 100) 的矩阵
    result = Fs @ AS_flat_reshaped
    result+=T[zs-1,xs]
    reshaped_result = result.reshape(Fs_z2, Fs_x2)
    # 将 reshaped_result 与 TT 比较，取最小值
    T[np.ix_(z3-1, x3)] = np.minimum(reshaped_result, TT)
    mxT = np.max(T[zs - 2:zs + 1, xs - 1:xs + 2])

    while True:
        indx = T + M <= mxT + mxV

        # 检查 indx 是否为空（在 Python 中为空意味着所有元素为 False）
        if not np.any(indx):
            indx = M == 0

        # 使用 np.where 找到 indx 中为 True 的索引
        idx, idz = np.where(indx.T)

        # 将 M 中对应 indx 为 True 的位置设置为 T0
        M[indx] = T0
        for i in range(len(idz)):
            z = idz[i]
            x = idx[i]
            mxT = max(mxT, T[z, x])
            AS = S[z + z2[:, np.newaxis], x + x2]
            z3 = z + z1
            x3 = x + x1
            TT = T[np.ix_(z3, x3)]
            AS_flat = AS.flatten()

            AS_flat_reshaped = AS_flat[:, np.newaxis]

            result = Fs @ AS_flat_reshaped
            result += T[z, x]
            reshaped_result = result.reshape(Fs_z2, Fs_x2)
        # 将 reshaped_result 与 TT 比较，取最小值
            T[np.ix_(z3 , x3)] = np.minimum(reshaped_result, TT)
        if np.all(M[iz[:, np.newaxis]-1, ix-1]):
            break
        mxT = np.max(T[idz, idx])

    T = T[iz[:, np.newaxis]-1, ix-1] * dx
    return T


def ricker(f, n, dt, t0=None, t1=None):
    if t0 is None:
        t0 = 1 / f

    # Determine if the output should be 2D based on the number of arguments
    is2d = t1 is not None

    # Create the wavelet and shift in time if needed
    T = dt * (n - 1)
    t = np.arange(0, T + dt, dt)
    tau = t - t0

    if not is2d:
        # 1D Ricker wavelet
        s = (1 - 2 * (tau ** 2) * (f ** 2) * (np.pi ** 2)) * np.exp(-tau ** 2 * (np.pi ** 2) * (f ** 2))
    else:
        # 2D Ricker wavelet
        t1_mesh, t2_mesh = np.meshgrid(tau, t - t1)
        s = (1 - 2 * (t1_mesh ** 2 + t2_mesh ** 2) * (f ** 2) * (np.pi ** 2)) * np.exp(
            -(t1_mesh ** 2 + t2_mesh ** 2) * (np.pi ** 2) * (f ** 2))

    return s, t

import numpy as np
from scipy.interpolate import interp2d

from scipy.interpolate import griddata
def gridinterp(A, x, z, x2, z2, method='linear'):
    """
    对电性质矩阵 A 进行插值，生成新的矩阵 A2。A 的行和列位置向量分别是 x 和 z，
    而生成的 A2 的行和列位置向量则是 x2 和 z2。插值方法默认为线性 ('linear')，
    也可以指定为 'nearest'（最近邻）、'cubic'（三次）或 'quintic'（五次）。

    用法：A2 = gridinterp(A, x, z, x2, z2, method)

    输入参数：
        A - 原始的电性质矩阵
        x - A 的行位置向量
        z - A 的列位置向量
        x2 - A2 的行位置向量
        z2 - A2 的列位置向量
        method - 插值方法，默认为 'linear'

    输出参数：
        A2 - 插值后的电性质矩阵
    """


    # 创建网格矩阵
    X, Z = np.meshgrid(x, z)
    X2, Z2 = np.meshgrid(x2, z2)

    # 将 X 和 Z 转换为一维数组以适应 griddata
    points = np.array([X.flatten(), Z.flatten()]).T
    values = A.flatten()

    # 执行插值
    grid_x, grid_z = np.meshgrid(x2, z2)
    interpolated_values = griddata(points, values, (grid_x, grid_z), method=method)
    interpolated_values=interpolated_values.T
    return interpolated_values

import numpy as np

def padgrid(A, x, z, n):
    """
    padgrid
    扩展电性质矩阵 A，在其每一边增加 n 个元素。这样做可以为模拟或计算提供额外的边界区域。
    新的矩阵 A2 会比原始矩阵 A 在每个方向上多出 2n 个元素。新矩阵的行和列位置向量分别是 x2 和 z2。
    在扩展区域中，原始矩阵的边界值会被简单地向外延伸。

    用法：[A2, x2, z2] = padgrid(A, x, z, n)

    输入参数：
        A - 原始的电性质矩阵
        x - A 的行位置向量
        z - A 的列位置向量
        n - 每边要添加的元素数量

    输出参数：
        A2 - 扩展后的电性质矩阵
        x2 - A2 的行位置向量
        z2 - A2 的列位置向量

    作者：James Irving
    日期：July 2005
    """

    # 计算新的位置向量
    dx = x[1] - x[0]  # 计算 x 方向上的间距
    dz = z[1] - z[0]  # 计算 z 方向上的间距
    x2 = np.arange(x[0] - n * dx, x[-1] + n * dx + 1e-10, dx)  # 计算扩展后的 x 位置向量
    z2 = np.arange(z[0] - n * dz, z[-1] + n * dz + 1e-10, dz)  # 计算扩展后的 z 位置向量

    # 扩展矩阵 A
    # 在左右两边各添加 n 列
    A2 = np.hstack((np.tile(A[:, [0]], (1, n)), A, np.tile(A[:, [-1]], (1, n))))
    # 在上下两边各添加 n 行
    A2 = np.vstack((np.tile(A2[[0], :], (n, 1)), A2, np.tile(A2[[-1], :], (n, 1))))

    return A2, x2, z2


# =========================
# 1. 你的拾取函数（可直接复用我之前发的）
# =========================

def pick_interface_dp(data,
                      smooth_sigma_traces=1.0,
                      smooth_sigma_time=0.0,
                      use_median=False,
                      amp_power=1.0,
                      max_jump=5,
                      jump_penalty=1.0,
                      normalize=True,
                      post_close_size=0):
    import numpy as np
    from scipy.ndimage import gaussian_filter1d, median_filter, binary_closing

    nz, nx = data.shape
    D = data.astype(float).copy()

    # 1. 创建 NaN 掩膜，确保不在 NaN 区域内找界面
    nan_mask = np.isnan(D)

    if use_median:
        D = median_filter(D, size=3)

    if smooth_sigma_traces > 0:
        D = gaussian_filter1d(D, sigma=smooth_sigma_traces, axis=1, mode='nearest')
    if smooth_sigma_time > 0:
        D = gaussian_filter1d(D, sigma=smooth_sigma_time, axis=0, mode='nearest')

    if normalize:
        tr_max = np.max(np.abs(D), axis=0, keepdims=True) + 1e-12
        Dn = np.abs(D) / tr_max
    else:
        Dn = np.abs(D)
        Dn = Dn / (np.max(Dn) + 1e-12)

    cost_volume = (1.0 - Dn) ** amp_power

    # 2. 给 NaN 区域赋极高的代价，确保 NaN 区域不被选中
    cost_volume[nan_mask] = np.inf

    dp = np.full_like(cost_volume, np.inf)
    path_idx = np.full((nz, nx), -1, dtype=int)
    dp[:, 0] = cost_volume[:, 0]

    for x in range(1, nx):
        for z in range(nz):
            z_min = max(0, z - max_jump)
            z_max = min(nz, z + max_jump + 1)

            # 排除 NaN 区域
            prev_cost = np.where(nan_mask[z_min:z_max, x - 1], np.inf,
                                 dp[z_min:z_max, x - 1] + jump_penalty * np.abs(np.arange(z_min, z_max) - z))

            best_prev_rel = np.argmin(prev_cost)
            dp[z, x] = cost_volume[z, x] + prev_cost[best_prev_rel]
            path_idx[z, x] = z_min + best_prev_rel

    picks_z = np.zeros(nx, dtype=int)
    picks_z[-1] = np.argmin(dp[:, -1])

    # 3. 路径回溯时跳过 NaN 区域
    for x in range(nx - 1, 0, -1):
        picks_z[x - 1] = path_idx[picks_z[x], x]

    # 4. 可选：形态学闭运算来补充断裂
    if post_close_size > 0:
        mask = np.zeros_like(data, dtype=bool)
        mask[picks_z, np.arange(nx)] = True
        mask = binary_closing(mask, structure=np.ones((post_close_size, 1)))
        new_picks = []
        for x in range(nx):
            rows = np.where(mask[:, x])[0]
            new_picks.append(picks_z[x] if len(rows) == 0 else int(np.median(rows)))
        picks_z = np.array(new_picks, dtype=int)

    return picks_z, cost_volume

# =========================
# 2. 画图函数 / Plotting helper
# =========================

def smooth_picks_spline(picks, smooth_factor=0.5, k=3):
    """
    使用平滑样条让界面线更顺滑
    picks : 1D array of ints
    smooth_factor : 控制平滑度，越大越平滑（可从 0.1~2 试）
    k : 样条阶数，3=三次样条
    """
    x = np.arange(len(picks))
    # s 参数大概可设为 smooth_factor * len(picks)
    spl = UnivariateSpline(x, picks, k=k, s=smooth_factor * len(picks))
    y_s = spl(x)
    return y_s.astype(int)
# def plot_interface(data.csv.csv, picks_z,
#                    dt=None, dx=None,
#                    cmap='gray', line_color='r',
#                    figsize=(10, 4), save_path=None):
#     """
#     在剖面上叠加拾取的界面。
#     Overlay picked horizon on the radar section.
#
#     Parameters
#     ----------
#     data.csv.csv : 2D ndarray (nz, nx)
#     picks_z : 1D ndarray (nx,)
#         Sample indices of the picked interface horizon.
#     dt : float or None
#         Sample interval in time/depth. If given, y-axis will be converted.
#     dx : float or None
#         Trace spacing. If given, x-axis will be converted.
#     cmap : str
#         Colormap for image.
#     line_color : str
#         Color of the interface line.
#     figsize : tuple
#         Figure size.
#     save_path : str or None
#         If provided, save the figure to this path.
#     """
#     nz, nx = data.csv.csv.shape
#     x_axis = np.arange(nx) if dx is None else np.arange(nx) * dx
#     z_axis = np.arange(nz) if dt is None else np.arange(nz) * dt
#
#     fig, ax = plt.subplots(figsize=figsize)
#     # origin='upper' 表示0样点在顶部；若你希望深度向下增加就别反转
#     im = ax.imshow(data.csv.csv, cmap=cmap, aspect='auto',
#                    extent=[x_axis[0], x_axis[-1], z_axis[-1], z_axis[0]])
#     ax.plot(x_axis, z_axis[picks_z], line_color, lw=2)
#
#     ax.set_xlabel('Trace' if dx is None else 'Distance')
#     ax.set_ylabel('Sample' if dt is None else 'Time/Depth')
#     ax.set_title('Picked Interface Overlay')
#     plt.colorbar(im, ax=ax, label='Amplitude')
#     #plt.gca().set_aspect('equal', adjustable='box')  # 横纵比例一样
#     plt.tight_layout()
#
#     if save_path:
#         plt.savefig(save_path, dpi=300, bbox_inches='tight')
#     plt.show()


def hei_correct(v, img: np.ndarray,dz,dt,
                flight: np.ndarray,
                domain: str = "time",
                c_air: float = 0.30) -> tuple[np.ndarray, np.ndarray]:
    """
    Height‑mute a migrated image and ALSO return n_mute per trace.

    Returns
    -------
    corrected      : 2‑D ndarray, same shape as img
    n_mute_arr     : 1‑D ndarray, length = n_x,
                     each element = rows removed for that trace
    """
    avg_column_1 = np.mean(v[:, 0])
    if img.ndim != 2:
        raise ValueError("`img` must be 2‑D (n_z, n_x).")

    n_z, n_x = img.shape

    # ---- 保证 flght 与道数一致 ---------------------------------
    flght = np.asarray(flight).ravel()
    if flght.size != n_x:
        x_old = np.arange(flight.size)
        x_new = np.linspace(0, flight.size - 1, n_x)
        flght = np.interp(x_new, x_old, flight)
        flight = np.interp(x_new, x_old, flight)

    # 如有 1/3 缩放，可在此统一处理
    flght = flght /(0.3/avg_column_1)

    corrected   = np.empty_like(img)
    n_mute_list = []                               # 用来收集每道 n_mute

    # ---- 主循环 -----------------------------------------------
    for j in range(n_x):
        if domain == "time":
            t_air_ns = 2.0 * flight[j] / c_air
            n_mute   = int(np.ceil(t_air_ns*1e-9 / dt))
            n_mute = min(n_mute, n_z)
            n_mute_list.append(n_mute)

            col = img[:, j]
            kept_part = col[n_mute:]  # 剩余波场
            pad_nan = np.full(n_mute, 0, dtype=img.dtype)
            corrected[:, j] = np.concatenate([kept_part, pad_nan])
        elif domain == "depth":
            n_mute   = int(np.ceil(flght[j] / dz))
            n_mute = min(n_mute, n_z)
            n_mute_list.append(n_mute)

            col = img[:, j]
            kept_part = col[n_mute:]  # 剩余波场
            pad_nan = np.full(n_mute, np.nan, dtype=img.dtype)
            corrected[:, j] = np.concatenate([kept_part, pad_nan])
        else:
            raise ValueError('`domain` must be "time" or "depth"')


    n_mute_arr = np.array(n_mute_list, dtype=int)
    return corrected, n_mute_arr





# ==========================================

def plot_interface_with_boreholes_kir(data, picks_z, topo_index, boreholes=None, topo_cor=0, elev=0, contrast=1,
                                      dt=None, dx=None, cmap='gray', line_color='r', figsize=(12, 8), save_path=None):
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft Ya Hei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.weight'] = 'bold'
    nz, nx = data.shape
    x_axis = np.arange(nx) if dx is None else np.arange(nx) * dx
    if topo_cor == 0:
        z_axis = np.arange(nz) if dt is None else np.arange(nz) * dt
    else:
        z_axis = np.arange(nz) if dt is None else max(elev) - np.arange(nz) * dt


    x_length_unit = data.shape[1] - 1
    z_length_unit = data.shape[0] - 1
    z_unit = 1  # 默认为 1
    data_ratio = (z_length_unit / x_length_unit)
    W = figsize[0]
    K_correction = 1.5
    H = W * data_ratio + K_correction
    fig_width = W
    fig_height = H



    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    vmin, vmax = compute_vmin_vmax(data, 1)
    denominator = vmax - vmin
    data_clipped = np.clip(data, vmin, vmax)
    data_norm = 2 * (data_clipped- vmin) / denominator - 1

    im = ax.imshow(data_norm, cmap=cmap, aspect='auto',
                   extent=[x_axis[0], x_axis[-1], z_axis[-1], z_axis[0]],
                   vmin=-1, vmax=1)
    # --- 关键修改部分：添加和设置颜色棒 ---

    # 1. 创建颜色棒 (colorbar)
    cbar = fig.colorbar(im, ax=ax)
    # 2. 设置颜色棒的标题/标签
    CBAR_LABEL = '信号幅度'  # 自定义标签文本
    CBAR_FONT_SIZE = 18  # 设定你想要的字体大小

    cbar.set_label(CBAR_LABEL, fontsize=CBAR_FONT_SIZE, fontweight='bold')

    # 3. (可选) 加大颜色棒的刻度标签 (数字) 字体
    cbar.ax.tick_params(labelsize=CBAR_FONT_SIZE - 2)
    if picks_z is None:
        print("Warning: picks_z is None, no interface will be plotted.")
    else:
        if picks_z.ndim == 1:
            picks_z_int = np.asarray(picks_z).astype(int)
            ax.plot(x_axis, z_axis[picks_z_int], color='r', lw=10, alpha=0.3)

    if topo_cor == 1:
        if boreholes is not None:
            times_new_roman_font = {'family': 'Times New Roman', 'weight': 'bold'}
            for borehole in boreholes:
                borehole_id, distance, depth = borehole
                ax.text(distance + 5, max(elev) - topo_index[round(distance / dx)] * dx + 5, borehole_id, ha='center',
                        va='top', fontsize=12, color='blue',fontdict=times_new_roman_font)
                ax.plot([distance, distance], max(elev) - [topo_index[round(distance / dx)] * dx,
                                                           topo_index[round(distance / dx)] * dx + max(depth)],
                        'b--',alpha=0.4)
                bar_half_length = 2.5
                for d in depth:
                    # 1. 计算横杆和文本的Y坐标
                    # 注意：这里的 bar_y_coord 代表 d 深度处的高程
                    bar_y_coord = max(elev) - (topo_index[round(distance / dx)] * dx + d)

                    # 2. 绘制水平横杆
                    ax.plot([distance - bar_half_length, distance + bar_half_length],
                            [bar_y_coord, bar_y_coord],
                            color='blue', lw=2, ls='-',alpha=0.6)
                    # 3. 绘制深度文本标签
                    # 文本Y坐标需要稍微向上偏移（+2）以避免与横杆重叠
                    text_y_coord = max(elev) - (topo_index[round(distance / dx)] * dx + d)-1.2
                    ax.text(distance+20, text_y_coord, f'{d}m',
                            ha='center', va='bottom', fontsize=12, color='blue',fontdict=times_new_roman_font)


    else:
        if boreholes is not None:
            times_new_roman_font = {'family': 'Times New Roman', 'weight': 'bold'}
            for borehole in boreholes:
                borehole_id, distance, depth = borehole
                ax.text(distance + 10, topo_index[round(distance / dx)] * dx + 1, borehole_id, ha='center',
                        va='top', fontsize=18, color='blue', fontdict=times_new_roman_font)

                ax.plot([distance, distance],
                        [topo_index[round(distance / dx)] * dx, topo_index[round(distance / dx)] * dx + max(depth)],
                        # <-- 关键：Y 坐标必须用方括号 [] 括起来
                        'b--',alpha=0.4)

                bar_half_length = 2.5
                for d in depth:
                    # 1. 计算横杆和文本的Y坐标
                    # 注意：这里的 bar_y_coord 代表 d 深度处的高程
                    bar_y_coord =  (topo_index[round(distance / dx)] * dx + d)
                    # 2. 绘制水平横杆
                    ax.plot([distance - bar_half_length, distance + bar_half_length],
                            [bar_y_coord, bar_y_coord],
                            color='blue', lw=2, ls='-',alpha=0.6)
                    # 3. 绘制深度文本标签
                    # 文本Y坐标需要稍微向上偏移（+2）以避免与横杆重叠
                    text_y_coord = (topo_index[round(distance / dx)] * dx + d)
                    ax.text(distance, text_y_coord, f'{d}m',
                            ha='center', va='bottom', fontsize=16, color='blue',fontdict=times_new_roman_font)

    # 调整坐标轴标签字体大小和刻度字体大小
    ax.set_xlabel('水平距离 (m)', fontsize=18, fontweight='bold')
    ax.set_ylabel('高程 (m)', fontsize=18, fontweight='bold')

    x_major_locator = ticker.MultipleLocator(40)
    ax.xaxis.set_major_locator(x_major_locator)

    y_major_locator = ticker.MultipleLocator(10)
    ax.yaxis.set_major_locator(y_major_locator)
    # 调整刻度标签的字体大小
    ax.tick_params(axis='both', which='major', labelsize=16)
    
    ax.set_title('Kirchhoff Migration profile')


    #设置窗口标题
    fig.canvas.manager.set_window_title('偏移成像结果')

    if save_path:
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
    plt.show()


# 使用示例 (请替换为你的实际数据)
# 例如:
# data.csv.csv = np.random.rand(200, 300)
# picks_z = np.arange(300) + 50 * np.sin(np.arange(300)/10)
# topo_index = np.zeros(300)
# plot_interface_with_boreholes_kir(data.csv.csv, picks_z, topo_index, dx=1, dt=1)

def plot_interface_with_boreholes_rtm(data, picks_z, topo_index, boreholes=None, topo_cor=0, elev=0,contrast=1,
                                          dt=None, dx=None, cmap='gray', line_color='r', figsize=(10, 4),
                                          save_path=None):
    """
    在剖面上叠加拾取的界面，并标注钻孔资料。
    Overlay picked horizon on the radar section and mark borehole locations.

    Parameters
    ----------
    data : 2D ndarray (nz, nx)
    picks_z : 1D ndarray (nx,)
        Sample indices of the picked interface horizon.
    boreholes : list of lists or None
        List of borehole locations. Each item is [distance, depth].
        Example: [[40, 22], [60, 18], [80, 25]] means borehole at 40m distance, 22m depth.
    dt : float or None
        Sample interval in time/depth. If given, y-axis will be converted.
    dx : float or None
        Trace spacing. If given, x-axis will be converted.
    cmap : str
        Colormap for image.
    line_color : str
        Color of the interface line.
    figsize : tuple
        Figure size.
    save_path : str or None
        If provided, save the figure to this path.
    """

        # 如果有钻孔资料，标注钻孔位置
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft Ya Hei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.weight'] = 'bold'
    nz, nx = data.shape
    x_axis = np.arange(nx) if dx is None else np.arange(nx) * dx
    if topo_cor == 0:
        z_axis = np.arange(nz) if dt is None else np.arange(nz) * dt
    else:
        z_axis = np.arange(nz) if dt is None else max(elev) - np.arange(nz) * dt

    fig, ax = plt.subplots(figsize=figsize)

    vmin, vmax = compute_vmin_vmax(data, contrast)
    im = ax.imshow(data, cmap=cmap, aspect='auto',
                   extent=[x_axis[0], x_axis[-1], z_axis[-1], z_axis[0]],
                   vmin=vmin, vmax=vmax)
    if picks_z is None:
        print("Warning: picks_z is None, no interface will be plotted.")
    else:
        if picks_z.ndim == 1:
            picks_z_int = np.asarray(picks_z).astype(int)
            ax.plot(x_axis, z_axis[picks_z_int], color='r', lw=10, alpha=0.3)

    if topo_cor == 1:
        if boreholes is not None:
            times_new_roman_font = {'family': 'Times New Roman', 'weight': 'bold'}
            for borehole in boreholes:
                borehole_id, distance, depth = borehole
                ax.text(distance + 5, max(elev) - topo_index[round(distance / dx)] * dx + 2, borehole_id, ha='center',
                        va='top', fontsize=14, color='blue',fontdict=times_new_roman_font)
                ax.plot([distance, distance], max(elev) - [topo_index[round(distance / dx)] * dx,
                                                           topo_index[round(distance / dx)] * dx + max(depth)],
                        'b--',alpha=0.4)
                bar_half_length = 2.5
                for d in depth:
                    # 1. 计算横杆和文本的Y坐标
                    # 注意：这里的 bar_y_coord 代表 d 深度处的高程
                    bar_y_coord = max(elev) - (topo_index[round(distance / dx)] * dx + d)

                    # 2. 绘制水平横杆
                    ax.plot([distance - bar_half_length, distance + bar_half_length],
                            [bar_y_coord, bar_y_coord],
                            color='blue', lw=2, ls='-',alpha=0.6)
                    # 3. 绘制深度文本标签
                    # 文本Y坐标需要稍微向上偏移（+2）以避免与横杆重叠
                    text_y_coord = max(elev) - (topo_index[round(distance / dx)] * dx + d)
                    ax.text(distance+10, text_y_coord, f'{d}m',
                            ha='center', va='bottom', fontsize=14, color='blue',fontdict=times_new_roman_font)


    else:
        if boreholes is not None:
            times_new_roman_font = {'family': 'Times New Roman', 'weight': 'bold'}
            for borehole in boreholes:
                borehole_id, distance, depth = borehole
                ax.text(distance + 10, topo_index[round(distance / dx)] * dx + 1, borehole_id, ha='center',
                        va='top', fontsize=14, color='blue', fontdict=times_new_roman_font)

                ax.plot([distance, distance],
                        [topo_index[round(distance / dx)] * dx, topo_index[round(distance / dx)] * dx + max(depth)],
                        # <-- 关键：Y 坐标必须用方括号 [] 括起来
                        'b--',
                        alpha=0.4)

                bar_half_length = 2.5
                for d in depth:
                    # 1. 计算横杆和文本的Y坐标
                    # 注意：这里的 bar_y_coord 代表 d 深度处的高程
                    bar_y_coord =  (topo_index[round(distance / dx)] * dx + d)
                    # 2. 绘制水平横杆
                    ax.plot([distance - bar_half_length, distance + bar_half_length],
                            [bar_y_coord, bar_y_coord],
                            color='blue', lw=2, ls='-',alpha=0.6)
                    # 3. 绘制深度文本标签
                    # 文本Y坐标需要稍微向上偏移（+2）以避免与横杆重叠
                    text_y_coord = (topo_index[round(distance / dx)] * dx + d)
                    ax.text(distance, text_y_coord, f'{d}m',
                            ha='center', va='bottom', fontsize=14, color='blue',fontdict=times_new_roman_font)

        # 调整坐标轴标签字体大小和刻度字体大小
    ax.set_xlabel('水平距离 (m)', fontsize=18, fontweight='bold')
    ax.set_ylabel('高程 (m)', fontsize=18, fontweight='bold')

        # 调整刻度标签的字体大小
    ax.tick_params(axis='both', which='major', labelsize=16)

    ax.set_title('Reverse Time Migration profile')

        # 调整 Colorbar 标签字体大小
    cbar = plt.colorbar(im, ax=ax, label='Amplitude')
    cbar.ax.set_ylabel('Amplitude', fontsize=14)

    # 设置窗口标题
    fig.canvas.manager.set_window_title('偏移成像结果')

    if save_path:
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
    plt.show()

def compute_vmin_vmax(data, contrast):
    """
    根据 contrast 返回 vmin/vmax，确保对比度调节平滑
    contrast = 0 表示原始范围
    contrast > 0 表示对比度增强
    contrast < 0 表示对比度降低
    """
    data_min = np.nanmin(data)
    data_max = np.nanmax(data)
    data_range = data_max - data_min

    # 设置 center 为 0，确保 vmin 和 vmax 的中间值是 0
    center = np.nanmean(data)
    # 非常小的 contrast 直接当作 0
    if contrast > 0:
        scale = 1 / (1 + contrast)  # 越大越强，范围越小
    else:
        scale = 1 - contrast  # contrast 为负，扩大范围

    new_half_range = (data_range / 2) * scale
    vmin = center - new_half_range
    vmax = center + new_half_range
    return vmin, vmax

def topogaphy_correct(data, topo, dx,dt,signal, fill_len=None):

    rows, cols = data.shape
    topo = np.asarray(topo).ravel()          # 保证一维
    x_old = np.arange(topo.size)
    x_new = np.linspace(0, topo.size - 1, cols)
    topo= np.interp(x_new, x_old, topo) # 线性插值

    if fill_len is None:
        fill_len = rows

    # 计算高度索引（与 MATLAB: round(height./dx)+1 接近）
    topo_index = np.round(topo / dx).astype(int)
    topo_index=max(topo_index)-topo_index
    pad_rows=max(topo_index)-min(topo_index)
    # 目标矩阵
    if signal==1:
        new_mat = np.full((rows + pad_rows, cols), np.nan, dtype=float)

    if signal==2:
        new_mat = np.full((rows + pad_rows, cols), 0, dtype=float)

    for i in range(cols):
        start = topo_index[i]
        if start < rows + pad_rows - 1:
            end = min(start + 1 + fill_len, rows + pad_rows)
            seg_len = end - (start + 1)
            if seg_len > 0:
                new_mat[start + 1:end, i] = data[:seg_len, i]

    return new_mat, pad_rows,topo_index

def higher_order_laplace_filter(data, order=1):
    """
    应用高阶拉普拉斯滤波器对数据进行滤波
    参数:
        data.csv.csv : 2D 或 1D ndarray, 输入的数据（图像或信号）
        order : int, 拉普拉斯滤波的阶数，默认为 2
    返回:
        filtered_data : ndarray, 滤波后的数据
    """
    filtered_data = np.copy(data)

    # 对数据进行多次拉普拉斯滤波

    filtered_data = laplace(filtered_data)

    return filtered_data

import numpy as np
import scipy.io as sio
from pathlib import Path
from scipy.ndimage import zoom
from typing import Tuple

def save_migrated_gpr(normalized_data: np.ndarray, number_samples: int, number_traces: int,
                      lon: np.ndarray,
                      lat: np.ndarray,
                      ground_elev: np.ndarray,
                      flight: np.ndarray,
                      dz: float,
                      dx: float,
                      out_root: Union[str, Path],
                      trace_tag: str = "trace"
                      ) -> Tuple[Path, Path]:
    """
    保存航空 GPR 偏移剖面：
    • 将数据调整为 number_samples 和 number_traces
    • 保存 .mat 备份 (RTM_profile, dx, dz)
    • 保存 .csv 格式数据，振幅列保留 NaN

    Parameters
    ----------
    normalized_data : (n_samples, n_traces) ndarray
        Migrated amplitudes with NaN denoting 'no data.csv.csv' below imaging depth.
    number_samples : int
        Desired number of samples (depth axis).
    number_traces  : int
        Desired number of traces (horizontal axis).
    lon, lat        : (n_traces,) ndarray
        Longitude / latitude.
    ground_elev     : (n_traces,) ndarray
        Ground elevation (m).
    flight          : (n_traces,) ndarray
        Flight height (m).
    dz, dx          : float
        Vertical sample step (m) / trace interval (m).
    out_root        : Parent directory; results saved to {out_root}/results/.
    trace_tag       : File name tag, e.g. "03" → res_03.mat, 03_migrated.csv.

    Returns
    -------
    mat_path, csv_path : Path
        Paths to saved .mat and .csv files.
    """
    # -------- 基本尺寸 --------
    n_samples, n_traces = normalized_data.shape
    depth_axis = np.arange(n_samples) * dz           # 深度轴 (m)
    depth_window = depth_axis[-1]

    # -------- 使用 zoom 调整数据尺寸 --------
    zoom_factors = [number_samples / n_samples, number_traces / n_traces]
    new_data = zoom(normalized_data, zoom_factors, order=1)  # 使用线性插值（order=1）

    # -------- 创建 results 目录 --------
    out_root = Path(out_root)
    results_dir = out_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # -------- 1) 保存 .mat --------
    mat_path = results_dir / f"res_{trace_tag}.mat"
    sio.savemat(mat_path,
                {"RTM_profile": new_data,
                 "dx": dx * n_traces / number_traces,   # 更新dx
                 "dz": dz * n_samples / number_samples}) # 更新dz

    # -------- 2) 写 CSV --------
    csv_path = results_dir / f"{trace_tag}_migrated.csv"
    header = [
        f"Number of Samples = {number_samples}",
        f"Depth window (m) = {new_data.shape[0] * dz:.3f}",
        f"Number of Traces = {number_traces}",
        f"Trace interval (m) = {dx * n_traces / number_traces:.3f}"
    ]

    with csv_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n")

        max_elev = np.max(ground_elev)  # 结果是 3.0
        # 将 ground_elev 的所有元素替换为其最大值
        new_elev = np.full_like(ground_elev, max_elev)
        # 计算更新后的高程
        new_depth_axis = np.linspace(0, depth_window, number_samples)
        new_elev_mat = new_elev - new_depth_axis[:, None]  # 更新后的高程 (m)
        new_data[-1, :] = np.nan

        for j in range(number_traces):
            block = np.column_stack((
                np.full(number_samples, lon[j]),               # 经度
                np.full(number_samples, lat[j]),               # 纬度
                new_elev_mat[:, j],                             # 高程
                new_data[:, j],                                 # 振幅 (含 NaN)
                np.full(number_samples, flight[j])             # 飞行高度
            ))
            np.savetxt(f,
                       block,
                       fmt="%.7f,%.8f,%.3f,%.7f,%.3f",
                       delimiter=",")

    print(f"✔ .mat saved → {mat_path}")
    print(f"✔ CSV saved → {csv_path}")
    return mat_path, csv_path




def mark_borehole_locations(data_points, depth_col='Depth', distance_col='Distance', xlim=None, ylim=None):
    """
    标注钻孔资料的位置，并绘制虚线表示水平距离。

    参数:
        data_points : list of lists or ndarray
            每个元素为 [水平距离, 深度] 的格式，如 [40, 22] 表示水平距离40m，深度22m。
        depth_col : str, optional
            深度列的标题，默认值 'Depth'。
        distance_col : str, optional
            水平距离列的标题，默认值 'Distance'。
        xlim : tuple, optional
            x 轴显示范围，默认为 None（自动调整）。
        ylim : tuple, optional
            y 轴显示范围，默认为 None（自动调整）。

    返回:
        None
    """

    plt.figure(figsize=(10, 6))

    for point in data_points:
        distance, depth = point
        plt.plot([distance, distance], [0, depth], 'b--')  # 蓝色虚线，水平距离为distance，深度为depth
        plt.text(distance, depth + 0.5, f'{depth}m', ha='center', va='bottom', fontsize=10, color='blue')  # 在上方标注深度

    # 设置图形的坐标轴范围
    if xlim:
        plt.xlim(xlim)
    if ylim:
        plt.ylim(ylim)

    plt.xlabel('Distance (m)')
    plt.ylabel('Depth (m)')
    plt.title('Borehole Locations')
    plt.gca().invert_yaxis()  # 反转 y 轴，使得深度从上到下递增
    plt.grid(True)
    plt.show()



import numpy as np
from scipy.ndimage import convolve, gaussian_filter
from scipy import linalg


def denoise_tv_bregman(image, lamda, max_iter=100, eps=1e-4):
    """
    Denoise image using Total Variation Bregman Iteration

    Parameters:
    - image : numpy.ndarray : Input noisy image (2D or 3D)
    - lamda : float : Regularization parameter (controls fidelity weight)
    - max_iter : int : Maximum number of iterations (default 100)
    - eps : float : Convergence threshold (default 1e-4)

    Returns:
    - out : numpy.ndarray : Denoised image
    - Phi_m : float : The norm of the difference between denoised image and original image
    """
    lamda2 = lamda * 1
    orig_min = np.min(image)
    orig_max = np.max(image)

    # Ensure image is at least 3D (for compatibility with grayscale/color)
    image = atleast_3d(image)
    rows, cols, dims = image.shape

    # Extend image boundaries to avoid edge effects
    image_padded = np.pad(image, [(1, 1), (1, 1), (0, 0)], mode='symmetric')

    # Initialize variables
    dx = np.zeros_like(image_padded)
    dy = np.zeros_like(image_padded)
    bx = np.zeros_like(image_padded)
    by = np.zeros_like(image_padded)

    # Bregman parameters
    mu = 1  # Rate for updating dual variables
    norm_factor = 1 + 4 * lamda

    # Iterative optimization
    for iter in range(max_iter):
        u_prev = image_padded[1:-1, 1:-1, :]

        # Calculate gradients
        ux = image_padded[1:rows + 1, 2:cols + 2, :] - u_prev
        uy = image_padded[2:rows + 2, 1:cols + 1, :] - u_prev

        # Update primal variables (TV + fidelity term)
        u_new = (lamda * (image_padded[2:rows + 2, 1:cols + 1, :] + image_padded[0:rows, 1:cols + 1, :] +
                          image_padded[1:rows + 1, 2:cols + 2, :] + image_padded[1:rows + 1, 0:cols, :] +
                          image + dx[1:rows + 1, 0:cols, :] - dx[1:rows + 1, 1:cols + 1, :] +
                          dy[0:rows, 1:cols + 1, :] - dy[1:rows + 1, 1:cols + 1, :] -
                          bx[1:rows + 1, 0:cols, :] + bx[1:rows + 1, 1:cols + 1, :] -
                          by[0:rows, 1:cols + 1, :] + by[1:rows + 1, 1:cols + 1, :])) / norm_factor

        # Update extended area values
        image_padded[1:rows + 1, 1:cols + 1, :] = u_new
        image_padded = fill_boundary(image_padded)  # Boundary optimization

        # Calculate convergence error
        residual = np.linalg.norm(u_new.flatten() - u_prev.flatten()) + lamda2 * np.linalg.norm(u_prev.flatten())
        if residual < eps:
            break

        # Update dual variables (Bregman iteration)
        tx = ux + bx[1:rows + 1, 1:cols + 1, :]
        ty = uy + by[1:rows + 1, 1:cols + 1, :]
        s = np.sqrt(tx ** 2 + ty ** 2) + 1e-6  # Avoid division by zero

        dx_new = (mu * s * tx) / (mu * s + 1)
        dy_new = (mu * s * ty) / (mu * s + 1)

        # Update Bregman parameters
        bx[1:rows + 1, 1:cols + 1, :] = bx[1:rows + 1, 1:cols + 1, :] + ux - dx_new
        by[1:rows + 1, 1:cols + 1, :] = by[1:rows + 1, 1:cols + 1, :] + uy - dy_new

        dx[1:rows + 1, 1:cols + 1, :] = dx_new
        dy[1:rows + 1, 1:cols + 1, :] = dy_new

    # Normalize and rescale the output
    out_normalized = (image_padded[1:-1, 1:-1, :] - np.min(image_padded)) / (
                np.max(image_padded) - np.min(image_padded))
    out = out_normalized * (orig_max - orig_min) + orig_min

    # Compute Phi_m (the norm of the difference between denoised and original image)
    Phi_m = np.linalg.norm(out.flatten() - image.flatten())

    return out[:,:,0]


def atleast_3d(image):
    """
    Ensure that the image is at least 3D.
    """
    if image.ndim < 3:
        image = image[..., np.newaxis]  # Add a singleton dimension if necessary
    return image


def fill_boundary(image):
    """
    Fill the boundary pixels to avoid boundary artifacts.
    """
    image[0, 1:-1, :] = image[1, 1:-1, :]
    image[-1, 1:-1, :] = image[-2, 1:-1, :]
    image[1:-1, 0, :] = image[1:-1, 1, :]
    image[1:-1, -1, :] = image[1:-1, -2, :]
    image[0, 0, :] = image[1, 1, :]
    image[0, -1, :] = image[1, -2, :]
    image[-1, 0, :] = image[-2, 1, :]
    image[-1, -1, :] = image[-2, -2, :]
    return image


def smooth2a(matrix_in, Nr, Nc=None):
    """
    Smooths 2D array data.csv.csv. Ignores NaN's.

    Parameters:
    matrix_in: 2D numpy array
        The original matrix to be smoothed.
    Nr: int
        Number of points to smooth along rows.
    Nc: int, optional
        Number of points to smooth along columns. If not specified, Nc = Nr.

    Returns:
    matrix_out: 2D numpy array
        Smoothed version of the original matrix.
    """
    if Nc is None:
        Nc = Nr

    # Get the shape of the input matrix
    row, col = matrix_in.shape

    # Create the sparse diagonal matrices eL and eR
    eL = spdiags(np.ones((2 * Nr + 1, row)), np.arange(-Nr, Nr + 1), row, row)
    eR = spdiags(np.ones((2 * Nc + 1, col)), np.arange(-Nc, Nc + 1), col, col)

    # Set NaN elements in matrix_in to zero for summing
    A = np.isnan(matrix_in)
    matrix_in[A] = 0

    # Normalize by counting the number of non-NaN elements
    nrmlize = eL @ (~A) @ eR
    nrmlize[A] = np.nan

    # Perform the smoothing operation (take the mean)
    matrix_out = eL @ matrix_in @ eR
    matrix_out = matrix_out / nrmlize

    return matrix_out
# =========================
# 3. 示例：生成假数据 & 运行
# =========================
from scipy import signal
def bandpass_filter(data, sampling_interval, low_cutoff, high_cutoff, filter_order=4):
    """
    对每一列信号进行带通滤波，频率范围在 low_cutoff 到 high_cutoff 之间。

    参数:
    data.csv.csv (numpy.ndarray): 输入的二维数据矩阵，形状为 (n_samples, n_signals)，
                           每列是一个信号样本。
    sampling_interval (float): 每个数据点的时间间隔，单位为秒。
    low_cutoff (float): 带通滤波器的低频截止频率，单位为 Hz。
    high_cutoff (float): 带通滤波器的高频截止频率，单位为 Hz。
    filter_order (int): 滤波器的阶数，默认为 4。

    返回:
    filtered_data (numpy.ndarray): 滤波后的信号数据。
    """
    # 计算采样频率

    sampling_rate = 1 / sampling_interval  # 采样频率

    # 归一化频率（带通滤波器要求频率在 [0, 1] 范围内，1代表采样频率的一半）
    low_norm = low_cutoff / (sampling_rate / 2)
    high_norm = high_cutoff / (sampling_rate / 2)

    # 检查归一化频率是否在有效范围内
    if low_norm <= 0 or high_norm >= 1:
        raise ValueError("Digital filter critical frequencies must be between 0 and 1.")

    # 设计带通滤波器
    b, a = signal.butter(N=filter_order, Wn=[low_norm, high_norm], btype='band')

    # 对每列信号应用滤波器
    filtered_data = np.zeros_like(data)
    for i in range(data.shape[1]):
        filtered_data[:, i] = signal.filtfilt(b, a, data[:, i])

    return filtered_data


def median_smoothing(data, size=3):
    """
    对每列数据进行中值滤波。

    参数:
    data.csv.csv (numpy.ndarray): 输入数据，形状为 (n_samples, n_signals)。
    size (int): 滤波窗口的大小。

    返回:
    smoothed_data (numpy.ndarray): 平滑后的数据。
    """
    smoothed_data = np.copy(data)
    for i in range(data.shape[1]):
        smoothed_data[:, i] = median_filter(data[:, i], size=size)
    return smoothed_data
