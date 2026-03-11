import numpy as np
import cupy as cp
import os
from FDTD.tools import gridinterp
from FDTD.tools import padgrid
from updatafwd import updatafwd,updatafwd_ini
from updatabwd import updatabwd,updatabwd_ini
import scipy.io
from numba import cuda
def rtm_gpu(v, sig1, coord, t, xprop, zprop, source, data, dz, npml, num_i, num_cal, num_parfor, SFCW,gpu_index):
    print(f'Task: 0.00%')
    cuda.select_device(gpu_index)
    c = 3e8  # 真空中的光速
    ep0 = 8.8541878176e-12  # 真空的介电常数
    mu0 = 1.2566370614e-6  # 真空的磁导率

    xdim = len(xprop)
    zdim = len(zprop)
    nx = xdim
    nz = zdim
    dx = dz


    x1 = np.arange(nx) * dx
    z1 = np.arange(nz) * dz
    x2 = np.arange(np.min(x1), np.max(x1)+dx / 2, dx / 2)
    z2 = np.arange(np.min(z1), np.max(z1)+dz / 2, dz / 2)

    xHx = x1[1:-1]
    zHz = z1[1:-1]
    xEy = xHx
    zEy = zHz

    nsrc = coord.shape[0]
    dt = t[1] - t[0]  # 时间步长
    numit = len(t)  # 迭代次数

    ep1 = c**2 / (v * 1e9)**2 * ep0
    mu1 = np.ones((nx, nz)) * mu0

    ep2 = gridinterp(ep1, x1, z1, x2, z2, method='nearest')
    mu2 = gridinterp(mu1, x1, z1, x2, z2, method='nearest')
    sig2 = gridinterp(sig1, x1, z1, x2, z2, method='nearest')

    ep, xprop, zprop = padgrid(ep2, x2, z2, 2 * npml + 1)
    mu, xprop, zprop = padgrid(mu2, x2, z2, 2 * npml + 1)
    sig, xprop, zprop = padgrid(sig2, x2, z2, 2 * npml + 1)

    nx = (len(xprop) + 1) // 2
    nz = (len(zprop) + 1) // 2
    srci = np.ceil(coord[:, 0] / dx) + npml, np.ceil(coord[:, 1] / dz) + npml

    maxsource = int(num_cal)
    m = np.arange(maxsource)
    nq = np.ceil(nsrc / maxsource)

    m1 = 4
    Kxmax = 5  # PML K_x 最大值
    Kzmax = 5  # PML K_z 最大值
    sigxmax = (m1 + 1) / (150 * np.pi * np.sqrt(ep / ep0) * dx)  # PML sigma_x 最大值
    sigzmax = (m1 + 1) / (150 * np.pi * np.sqrt(ep / ep0) * dz)  # PML sigma_z 最大值
    alpha = 0  # PML alpha 参数

    g = npml + 20

    kpmlLout = 1
    kpmlLin = 2 * npml + 2
    kpmlRin = len(xprop) - (2 * npml + 2) + 1
    kpmlRout = len(xprop)
    lpmlTout = 1
    lpmlTin = 2 * npml + 2
    lpmlBin = len(zprop) - (2 * npml + 2) + 1
    lpmlBout = len(zprop)

    xdel = np.zeros((len(xprop), len(zprop)))
    k = np.arange(kpmlLout, kpmlLin)
    xdel[k, :] = np.tile((kpmlLin - k) / (2 * npml), (len(zprop), 1)).T
    k = np.arange(kpmlRin, kpmlRout)
    xdel[k, :] = np.tile((k - kpmlRin) / (2 * npml), (len(zprop), 1)).T

    zdel = np.zeros((len(xprop), len(zprop)))
    l = np.arange(lpmlTout, lpmlTin)
    zdel[:, l] = np.tile((lpmlTin - l) / (2 * npml), (len(xprop), 1))
    l = np.arange(lpmlBin, lpmlBout)
    zdel[:, l] = np.tile((l - lpmlBin) / (2 * npml), (len(xprop), 1))

    sigx = sigxmax * xdel**m1
    sigz = sigzmax * zdel**m1
    Kx = 1 + (Kxmax - 1) * xdel**m1
    Kz = 1 + (Kzmax - 1) * zdel**m1

    dt=float(dt)
    sig = cp.array(sig)
    ep = cp.array(ep)
    mu = cp.array(mu)
    Kx = cp.array(Kx)
    Kz = cp.array(Kz)
    sigx = cp.array(sigx)
    sigz = cp.array(sigz)
    m= cp.array(m)
    alpha = cp.array(alpha)

    Ca = cp.array((1 - dt * sig / (2 * ep)) / (1 + dt * sig / (2 * ep)), dtype=cp.float32)
    Cbx = cp.array(dt / ep / ((1 + dt * sig / (2 * ep)) * 24 * dx * Kx), dtype=cp.float32)
    Cbz = cp.array(dt / ep / ((1 + dt * sig / (2 * ep)) * 24 * dz * Kz), dtype=cp.float32)
    Cc = cp.array(dt / ep / (1 + dt * sig / (2 * ep)), dtype=cp.float32)
    Dbx = cp.array(dt / (mu * Kx * 24 * dx), dtype=cp.float32)
    Dbz = cp.array(dt / (mu * Kz * 24 * dz), dtype=cp.float32)
    Dc = cp.array(dt / mu, dtype=cp.float32)
    Bx = cp.array(cp.exp(-(sigx / Kx + alpha) * (dt / ep0)), dtype=cp.float32)
    Bz = cp.array(cp.exp(-(sigz / Kz + alpha) * (dt / ep0)), dtype=cp.float32)
    Ax = cp.array(sigx / (sigx * Kx + Kx**2 * alpha + 1e-20) * (Bx - 1) / (24 * dx), dtype=cp.float32)
    Az = cp.array(sigz / (sigz * Kz + Kz**2 * alpha + 1e-20) * (Bz - 1) / (24 * dz), dtype=cp.float32)

    image3 = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)
    image4 = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)

    # 计算 i1 和 j1
    i1 = cp.arange(2, nx - 1)  # MATLAB: 2:nx-2
    j1 = cp.arange(3, nz - 1)  # MATLAB: 3:nz-2

    # 计算 k1 和 l1
    k1 = 2 * i1
    l1 = 2 * j1 - 1

    # 计算 kp1 和 lp1
    kp1 = k1[(k1 <= kpmlLin) | (k1 >= kpmlRin)]
    lp1 = l1[(l1 <= lpmlTin) | (l1 >= lpmlBin)]

    # 计算 ki1 和 ii1
    ki1 = k1[(k1 > kpmlLin) & (k1 < kpmlRin)]
    ip1 = (kp1 // 2).astype(int)
    jp1 = ((lp1 + 1) // 2).astype(int)
    ii1 = (ki1 // 2).astype(int)

    # 计算 i2 和 j2
    i2 = cp.arange(3, nx - 1)  # MATLAB: 3:nx-2
    j2 = cp.arange(2, nz - 1)  # MATLAB: 2:nz-2

    # 计算 k2 和 l2
    k2 = 2 * i2 - 1
    l2 = 2 * j2

    # 计算 kp2 和 lp2
    kp2 = k2[(k2 <= kpmlLin) | (k2 >= kpmlRin)]
    lp2 = l2[(l2 <= lpmlTin) | (l2 >= lpmlBin)]

    # 计算 ki2 和 ii2
    ki2 = k2[(k2 > kpmlLin) & (k2 < kpmlRin)]
    ip2 = ((kp2 + 1) // 2).astype(int)
    jp2 = (lp2 // 2).astype(int)
    ii2 = ((ki2 + 1) // 2).astype(int)

    # 计算 i3 和 j3
    i3 = cp.arange(2, nx - 1)  # MATLAB: 2:nx-2
    j3 = cp.arange(2, nz - 1)  # MATLAB: 2:nz-2

    # 计算 k3 和 l3
    k3 = 2 * i3
    l3 = 2 * j3

    # 计算 kp3 和 lp3
    kp3 = k3[(k3 <= kpmlLin) | (k3 >= kpmlRin)]
    lp3 = l3[(l3 <= lpmlTin) | (l3 >= lpmlBin)]

    # 计算 ki3 和 ii3
    ki3 = k3[(k3 > kpmlLin) & (k3 < kpmlRin)]
    ip3 = (kp3 // 2).astype(int)
    jp3 = (lp3 // 2).astype(int)
    ii3 = (ki3 // 2).astype(int)

    # 初始化电磁场分量及其差分的 GPU 数组
    Ey = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Ey 电场分量
    Hx = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # Hx 磁场分量
    Hz = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # Hz 磁场分量
    Eydiffx = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # Ey 分量沿 x 方向的差分
    Eydiffz = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # Ey 分量沿 z 方向的差分
    Hxdiffz = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Hx 分量沿 z 方向的差分
    Hzdiffx = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Hz 分量沿 x 方向的差分

    # 初始化 PML 参数的 GPU 数组
    PEyx = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Ey 分量沿 x 方向的参数
    PEyz = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Ey 分量沿 z 方向的参数
    PHx = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # PML 中 Hx 分量的参数
    PHz = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Hz 分量的参数
    endpic= cp.zeros((nx-1, nz - 1, numit), dtype=cp.float32)  # PML 中 Hz 分量的参数
    data1 = cp.array(data, dtype=cp.float32)

    # 初始化进度条
    for s1 in range(1, int(nq) + 1):
        # 初始化电磁场分量及其差分的 GPU 数组
        Ey.fill(0)
        Hx.fill(0)
        Hz.fill(0)
        Eydiffx.fill(0)
        Eydiffz.fill(0)
        Hxdiffz.fill(0)
        Hzdiffx.fill(0)

        # 初始化 PML 参数的 GPU 数组
        PEyx.fill(0)
        PEyz.fill(0)
        PHx.fill(0)
        PHz.fill(0)

        if s1 == 1:
            endpic = updatafwd(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx, Hxdiffz, Hzdiffx,
                               i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3, l3, kp3, lp3, ki3, ip3, jp3, ii3,
                               m, numit, source, npml, g, srci, maxsource, int(nq), s1, SFCW,endpic)

            Ey.fill(0)
            Hx.fill(0)
            Hz.fill(0)
            Eydiffx.fill(0)
            Eydiffz.fill(0)
            Hxdiffz.fill(0)
            Hzdiffx.fill(0)
            PEyx.fill(0)
            PEyz.fill(0)
            PHx.fill(0)
            PHz.fill(0)
            image3.fill(0)
            image4.fill(0)
            PHz.fill(0)
            image3, image4 = updatabwd(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx, Hxdiffz, Hzdiffx,
                                       i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3, l3, kp3, lp3, ki3, ip3, jp3, ii3,
                                       numit, srci, data1, npml, g, endpic, image3, image4, maxsource, int(nq), m, s1)

        else:
            Ey.fill(0)
            Hx.fill(0)
            Hz.fill(0)
            Eydiffx.fill(0)
            Eydiffz.fill(0)
            Hxdiffz.fill(0)
            Hzdiffx.fill(0)
            PEyx.fill(0)
            PEyz.fill(0)
            PHx.fill(0)
            PHz.fill(0)
            image3.fill(0)
            image4.fill(0)
            image3, image4 = updatabwd(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx, Hxdiffz, Hzdiffx,
                                       i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3, l3, kp3, lp3, ki3, ip3, jp3, ii3,
                                       numit, srci, data1, npml, g, endpic, image3, image4, maxsource, int(nq), m, s1)

        im1 = cp.asnumpy(image3)
        im2 = cp.asnumpy(image4)
        current_folder = os.getcwd()

        folder_path1 = os.path.join(current_folder, 'tools', 'image3')
        folder_path2 = os.path.join(current_folder, 'tools', 'image4')
        file_name1 = f'result_{int(nq * (num_i) + s1)}.mat'
        file_name2 = f'result_{int(nq * (num_i) + s1)}.mat'
        full_file_path1 = os.path.join(folder_path1, file_name1)
        full_file_path2 = os.path.join(folder_path2, file_name2)

        scipy.io.savemat(full_file_path1, {'im1': im1})
        scipy.io.savemat(full_file_path2, {'im2': im2})

        if num_parfor == 1:
            progress = 100 * s1 / int(nq)
            print(f'Task: {progress:.2f} %')

def rtm_gpu_ini(v, sig1, coord, t, xprop, zprop, source, data, dz, npml,chunk_indices, num_cal, num_parfor, SFCW,gpu_index):
    cuda.select_device(gpu_index)

    c = 3e8  # 真空中的光速
    ep0 = 8.8541878176e-12  # 真空的介电常数
    mu0 = 1.2566370614e-6  # 真空的磁导率

    xdim = len(xprop)
    zdim = len(zprop)
    nx = xdim
    nz = zdim
    dx = dz


    x1 = np.arange(nx) * dx
    z1 = np.arange(nz) * dz
    x2 = np.arange(np.min(x1), np.max(x1)+dx / 2, dx / 2)
    z2 = np.arange(np.min(z1), np.max(z1)+dz / 2, dz / 2)

    xHx = x1[1:-1]
    zHz = z1[1:-1]
    xEy = xHx
    zEy = zHz

    nsrc = coord.shape[0]
    dt = t[1] - t[0]  # 时间步长
    numit = len(t)  # 迭代次数

    ep1 = c**2 / (v * 1e9)**2 * ep0
    mu1 = np.ones((nx, nz)) * mu0

    ep2 = gridinterp(ep1, x1, z1, x2, z2, method='nearest')
    mu2 = gridinterp(mu1, x1, z1, x2, z2, method='nearest')
    sig2 = gridinterp(sig1, x1, z1, x2, z2, method='nearest')

    ep, xprop, zprop = padgrid(ep2, x2, z2, 2 * npml + 1)
    mu, xprop, zprop = padgrid(mu2, x2, z2, 2 * npml + 1)
    sig, xprop, zprop = padgrid(sig2, x2, z2, 2 * npml + 1)

    nx = (len(xprop) + 1) // 2
    nz = (len(zprop) + 1) // 2
    srci = np.ceil(coord[:, 0] / dx) + npml, np.ceil(coord[:, 1] / dz) + npml

    maxsource = int(num_cal)
    m = np.arange(maxsource)
    nq = np.ceil(nsrc / maxsource)

    m1 = 4
    Kxmax = 5  # PML K_x 最大值
    Kzmax = 5  # PML K_z 最大值
    sigxmax = (m1 + 1) / (150 * np.pi * np.sqrt(ep / ep0) * dx)  # PML sigma_x 最大值
    sigzmax = (m1 + 1) / (150 * np.pi * np.sqrt(ep / ep0) * dz)  # PML sigma_z 最大值
    alpha = 0  # PML alpha 参数

    g = npml + 20

    kpmlLout = 1
    kpmlLin = 2 * npml + 2
    kpmlRin = len(xprop) - (2 * npml + 2) + 1
    kpmlRout = len(xprop)
    lpmlTout = 1
    lpmlTin = 2 * npml + 2
    lpmlBin = len(zprop) - (2 * npml + 2) + 1
    lpmlBout = len(zprop)

    xdel = np.zeros((len(xprop), len(zprop)))
    k = np.arange(kpmlLout, kpmlLin)
    xdel[k, :] = np.tile((kpmlLin - k) / (2 * npml), (len(zprop), 1)).T
    k = np.arange(kpmlRin, kpmlRout)
    xdel[k, :] = np.tile((k - kpmlRin) / (2 * npml), (len(zprop), 1)).T

    zdel = np.zeros((len(xprop), len(zprop)))
    l = np.arange(lpmlTout, lpmlTin)
    zdel[:, l] = np.tile((lpmlTin - l) / (2 * npml), (len(xprop), 1))
    l = np.arange(lpmlBin, lpmlBout)
    zdel[:, l] = np.tile((l - lpmlBin) / (2 * npml), (len(xprop), 1))

    sigx = sigxmax * xdel**m1
    sigz = sigzmax * zdel**m1
    Kx = 1 + (Kxmax - 1) * xdel**m1
    Kz = 1 + (Kzmax - 1) * zdel**m1

    dt=float(dt)
    sig = cp.array(sig)
    ep = cp.array(ep)
    mu = cp.array(mu)
    Kx = cp.array(Kx)
    Kz = cp.array(Kz)
    sigx = cp.array(sigx)
    sigz = cp.array(sigz)
    m= cp.array(m)
    alpha = cp.array(alpha)

    Ca = cp.array((1 - dt * sig / (2 * ep)) / (1 + dt * sig / (2 * ep)), dtype=cp.float32)
    Cbx = cp.array(dt / ep / ((1 + dt * sig / (2 * ep)) * 24 * dx * Kx), dtype=cp.float32)
    Cbz = cp.array(dt / ep / ((1 + dt * sig / (2 * ep)) * 24 * dz * Kz), dtype=cp.float32)
    Cc = cp.array(dt / ep / (1 + dt * sig / (2 * ep)), dtype=cp.float32)
    Dbx = cp.array(dt / (mu * Kx * 24 * dx), dtype=cp.float32)
    Dbz = cp.array(dt / (mu * Kz * 24 * dz), dtype=cp.float32)
    Dc = cp.array(dt / mu, dtype=cp.float32)
    Bx = cp.array(cp.exp(-(sigx / Kx + alpha) * (dt / ep0)), dtype=cp.float32)
    Bz = cp.array(cp.exp(-(sigz / Kz + alpha) * (dt / ep0)), dtype=cp.float32)
    Ax = cp.array(sigx / (sigx * Kx + Kx**2 * alpha + 1e-20) * (Bx - 1) / (24 * dx), dtype=cp.float32)
    Az = cp.array(sigz / (sigz * Kz + Kz**2 * alpha + 1e-20) * (Bz - 1) / (24 * dz), dtype=cp.float32)

    image3 = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)
    image4 = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)

    # 计算 i1 和 j1
    i1 = cp.arange(2, nx - 1)  # MATLAB: 2:nx-2
    j1 = cp.arange(3, nz - 1)  # MATLAB: 3:nz-2

    # 计算 k1 和 l1
    k1 = 2 * i1
    l1 = 2 * j1 - 1

    # 计算 kp1 和 lp1
    kp1 = k1[(k1 <= kpmlLin) | (k1 >= kpmlRin)]
    lp1 = l1[(l1 <= lpmlTin) | (l1 >= lpmlBin)]

    # 计算 ki1 和 ii1
    ki1 = k1[(k1 > kpmlLin) & (k1 < kpmlRin)]
    ip1 = (kp1 // 2).astype(int)
    jp1 = ((lp1 + 1) // 2).astype(int)
    ii1 = (ki1 // 2).astype(int)

    # 计算 i2 和 j2
    i2 = cp.arange(3, nx - 1)  # MATLAB: 3:nx-2
    j2 = cp.arange(2, nz - 1)  # MATLAB: 2:nz-2

    # 计算 k2 和 l2
    k2 = 2 * i2 - 1
    l2 = 2 * j2

    # 计算 kp2 和 lp2
    kp2 = k2[(k2 <= kpmlLin) | (k2 >= kpmlRin)]
    lp2 = l2[(l2 <= lpmlTin) | (l2 >= lpmlBin)]

    # 计算 ki2 和 ii2
    ki2 = k2[(k2 > kpmlLin) & (k2 < kpmlRin)]
    ip2 = ((kp2 + 1) // 2).astype(int)
    jp2 = (lp2 // 2).astype(int)
    ii2 = ((ki2 + 1) // 2).astype(int)

    # 计算 i3 和 j3
    i3 = cp.arange(2, nx - 1)  # MATLAB: 2:nx-2
    j3 = cp.arange(2, nz - 1)  # MATLAB: 2:nz-2

    # 计算 k3 和 l3
    k3 = 2 * i3
    l3 = 2 * j3

    # 计算 kp3 和 lp3
    kp3 = k3[(k3 <= kpmlLin) | (k3 >= kpmlRin)]
    lp3 = l3[(l3 <= lpmlTin) | (l3 >= lpmlBin)]

    # 计算 ki3 和 ii3
    ki3 = k3[(k3 > kpmlLin) & (k3 < kpmlRin)]
    ip3 = (kp3 // 2).astype(int)
    jp3 = (lp3 // 2).astype(int)
    ii3 = (ki3 // 2).astype(int)

    # 初始化电磁场分量及其差分的 GPU 数组
    Ey = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Ey 电场分量
    Hx = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # Hx 磁场分量
    Hz = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # Hz 磁场分量
    Eydiffx = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # Ey 分量沿 x 方向的差分
    Eydiffz = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # Ey 分量沿 z 方向的差分
    Hxdiffz = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Hx 分量沿 z 方向的差分
    Hzdiffx = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # Hz 分量沿 x 方向的差分

    # 初始化 PML 参数的 GPU 数组
    PEyx = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Ey 分量沿 x 方向的参数
    PEyz = cp.zeros((nx - 1, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Ey 分量沿 z 方向的参数
    PHx = cp.zeros((nx - 1, nz, maxsource), dtype=cp.float32)  # PML 中 Hx 分量的参数
    PHz = cp.zeros((nx, nz - 1, maxsource), dtype=cp.float32)  # PML 中 Hz 分量的参数
    endpic= cp.zeros((nx-1, nz - 1, numit,maxsource), dtype=cp.float32)  # PML 中 Hz 分量的参数
    data1 = cp.array(data, dtype=cp.float32)

    # 初始化进度条
    for s1 in range(1):
        # 初始化电磁场分量及其差分的 GPU 数组
        Ey.fill(0)
        Hx.fill(0)
        Hz.fill(0)
        Eydiffx.fill(0)
        Eydiffz.fill(0)
        Hxdiffz.fill(0)
        Hzdiffx.fill(0)

        # 初始化 PML 参数的 GPU 数组
        PEyx.fill(0)
        PEyz.fill(0)
        PHx.fill(0)
        PHz.fill(0)


        endpic = updatafwd_ini(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx, Hxdiffz, Hzdiffx,
                               i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3, l3, kp3, lp3, ki3, ip3, jp3, ii3,
                               m, numit, source, npml, g, srci, maxsource, int(nq), s1, SFCW,endpic)

        Ey.fill(0)
        Hx.fill(0)
        Hz.fill(0)
        Eydiffx.fill(0)
        Eydiffz.fill(0)
        Hxdiffz.fill(0)
        Hzdiffx.fill(0)
        PEyx.fill(0)
        PEyz.fill(0)
        PHx.fill(0)
        PHz.fill(0)
        image3.fill(0)
        image4.fill(0)
        PHz.fill(0)
        image3, image4 = updatabwd_ini(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx, Hxdiffz, Hzdiffx,
                                       i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3, l3, kp3, lp3, ki3, ip3, jp3, ii3,
                                       numit, srci, data1, npml, g, endpic, image3, image4, maxsource, int(nq), m, s1)

        im1 = cp.asnumpy(image3)
        im2 = cp.asnumpy(image4)
        current_folder = os.getcwd()

        folder_path1 = os.path.join(current_folder, 'tools', 'image3')
        folder_path2 = os.path.join(current_folder, 'tools', 'image4')
        file_name1 = f'result_{chunk_indices}.mat'
        file_name2 = f'result_{chunk_indices}.mat'
        full_file_path1 = os.path.join(folder_path1, file_name1)
        full_file_path2 = os.path.join(folder_path2, file_name2)

        scipy.io.savemat(full_file_path1, {'im1': im1})
        scipy.io.savemat(full_file_path2, {'im2': im2})
