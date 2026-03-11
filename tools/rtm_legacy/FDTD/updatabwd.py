import numpy as np
import cupy as cp
import matplotlib.pyplot as plt
def updatabwd(Ey, Hx, Hz, Dbz, Dbx, Bz, Bx, Az, Ax, Dc, Ca, Cbx, Cbz, Cc, PEyx, PEyz, PHx, PHz, Eydiffz, Eydiffx,
              Hxdiffz, Hzdiffx,i1, j1, k1, l1, kp1, lp1, ki1, ip1, jp1, ii1, i2, j2, k2, l2, kp2, lp2, ki2, ip2, jp2, ii2, i3, j3, k3,
              l3, kp3, lp3, ki3, ip3, jp3, ii3, numit, srci, data, maxsource, m1, s1):
    # 添加额外的维度以匹配 Ey, Hx, Hz等数组
    i1 = i1[:, cp.newaxis, cp.newaxis]  # i1 shape: (len, 1, 1)
    j1 = j1[cp.newaxis, :, cp.newaxis]  # j1 shape: (1, len, 1)
    l1 = l1[cp.newaxis, :]
    l2 = l2[cp.newaxis, :]
    l3 = l3[cp.newaxis, :]
    k1 = k1[:, cp.newaxis]
    k2 = k2[:, cp.newaxis]

    i2 = i2[:, cp.newaxis, cp.newaxis]
    j2 = j2[cp.newaxis, :, cp.newaxis]

    i3 = i3[:, cp.newaxis, cp.newaxis]
    j3 = j3[cp.newaxis, :, cp.newaxis]

    k3 = k3[:, cp.newaxis]
    # 将一维索引变量调整为三维数组操作所需的形状
    # 添加额外的维度来匹配 Ey, Hx, Hz 等三维数组
    # 对 kp1, kp2, kp3 等进行调整
    kp1 = kp1[:, cp.newaxis]
    kp2 = kp2[:, cp.newaxis]
    kp3 = kp3[:, cp.newaxis]
    # 对 lp1, lp2, lp3 等进行调整
    lp1 = lp1[cp.newaxis, :]
    lp2 = lp2[cp.newaxis, :]
    lp3 = lp3[cp.newaxis, :]
    # 对 ki1, ki2, ki3 等进行调整
    ki1 = ki1[:, cp.newaxis]
    ki2 = ki2[:, cp.newaxis]
    ki3 = ki3[:, cp.newaxis]
    # 对 ip1, ip2, ip3 等进行调整
    ip1 = ip1[:, cp.newaxis, cp.newaxis]
    ip2 = ip2[:, cp.newaxis, cp.newaxis]
    ip3 = ip3[:, cp.newaxis, cp.newaxis]
    # 对 jp1, jp2, jp3 等进行调整
    jp1 = jp1[cp.newaxis, :, cp.newaxis]
    jp2 = jp2[cp.newaxis, :, cp.newaxis]
    jp3 = jp3[cp.newaxis, :, cp.newaxis]
    # 对 ii1, ii2, ii3 等进行调整
    ii1 = ii1[:, cp.newaxis, cp.newaxis]
    ii2 = ii2[:, cp.newaxis, cp.newaxis]
    ii3 = ii3[:, cp.newaxis, cp.newaxis]
    m1 = m1[cp.newaxis,cp.newaxis, :]  # Python中索引从0开始，m1=1 -> m1=0
    for it in range(numit):
        # 更新 Hx 组件
        Eydiffz[i1-1, j1-1, m1] = -Ey[i1 - 1, j1, m1] + 27 * Ey[i1 - 1, j1 - 1, m1] - 27 * Ey[i1 - 1, j1 - 2, m1] + Ey[
            i1 - 1, j1 - 3, m1]
        # 更新 Hx 组件
        Hx[i1 - 1, j1 - 1, m1] -= Dbz[k1 - 1, l1 - 1][:, :, cp.newaxis] * Eydiffz[i1-1, j1-1, m1]
        # 仅应用于 PML 区域的更新
        PHx[ip1 - 1, j1 - 1, m1] = (Bz[kp1 - 1, l1 - 1][:, :, cp.newaxis] * PHx[ip1 - 1, j1 - 1, m1]) + (
                Az[kp1 - 1, l1 - 1][:, :, cp.newaxis] * Eydiffz[ip1 - 1, j1 - 1, m1])

        PHx[ii1 - 1, jp1 - 1, m1] = (Bz[ki1 - 1, lp1 - 1][:, :, cp.newaxis] * PHx[ii1 - 1, jp1 - 1, m1]) + (
                Az[ki1 - 1, lp1 - 1][:, :, cp.newaxis] * Eydiffz[ii1 - 1, jp1 - 1, m1])

        Hx[ip1 - 1, j1 - 1, m1] -= Dc[kp1 - 1, l1 - 1][:, :, cp.newaxis] * PHx[ip1 - 1, j1 - 1, m1]
        Hx[ii1 - 1, jp1 - 1, m1] -= Dc[ki1 - 1, lp1 - 1][:, :, cp.newaxis] * PHx[ii1 - 1, jp1 - 1, m1]

        # 更新 Hz 组件
        # 计算 Eydiffx
        Eydiffx[i2 - 1, j2 - 1, m1] = -Ey[i2, j2 - 1, m1] + 27 * Ey[i2 - 1, j2 - 1, m1] - 27 * Ey[i2 - 2, j2 - 1, m1] + \
                                      Ey[i2 - 3, j2 - 1, m1]
        # 更新 Hz 组件
        Hz[i2 - 1, j2 - 1, m1] += Dbx[k2 - 1, l2 - 1][:, :, cp.newaxis] * Eydiffx[i2 - 1, j2 - 1, m1]

        # 仅应用于 PML 区域的更新
        # 更新 PHz 组件
        PHz[ip2 - 1, j2 - 1, m1] = (Bx[kp2 - 1, l2 - 1][:, :, cp.newaxis] * PHz[ip2 - 1, j2 - 1, m1]) + (
                Ax[kp2 - 1, l2 - 1][:, :, cp.newaxis] * Eydiffx[ip2 - 1, j2 - 1, m1])
        PHz[ii2 - 1, jp2 - 1, m1] = (Bx[ki2 - 1, lp2 - 1][:, :, cp.newaxis] * PHz[ii2 - 1, jp2 - 1, m1]) + (
                Ax[ki2 - 1, lp2 - 1][:, :, cp.newaxis] * Eydiffx[ii2 - 1, jp2 - 1, m1])

        # 更新 Hz 组件
        Hz[ip2 - 1, j2 - 1, m1] += Dc[kp2 - 1, l2 - 1][:, :, cp.newaxis] * PHz[ip2 - 1, j2 - 1, m1]
        Hz[ii2 - 1, jp2 - 1, m1] += Dc[ki2 - 1, lp2 - 1][:, :, cp.newaxis] * PHz[ii2 - 1, jp2 - 1, m1]

        # 计算 Hxdiffz 和 Hzdiffx
        Hxdiffz[i3 - 1, j3 - 1, m1] = -Hx[i3 - 1, j3 + 1, m1] + 27 * Hx[i3 - 1, j3, m1] - 27 * Hx[i3 - 1, j3 - 1, m1] + \
                                      Hx[i3 - 1, j3 - 2, m1]
        Hzdiffx[i3 - 1, j3 - 1, m1] = -Hz[i3 + 1, j3 - 1, m1] + 27 * Hz[i3, j3 - 1, m1] - 27 * Hz[i3 - 1, j3 - 1, m1] + \
                                      Hz[i3 - 2, j3 - 1, m1]

        # 更新 Ey 组件
        Ey[i3 - 1, j3 - 1, m1] = (Ca[k3 - 1, l3 - 1][:, :, cp.newaxis] * Ey[i3 - 1, j3 - 1, m1]) + (
                Cbx[k3 - 1, l3 - 1][:, :, cp.newaxis] * Hzdiffx[i3 - 1, j3 - 1, m1]) - (
                                         Cbz[k3 - 1, l3 - 1][:, :, cp.newaxis] * Hxdiffz[i3 - 1, j3 - 1, m1])
        # 仅应用于 PML 区域的更新
        # 更新 PEyx 组件
        PEyx[ip3 - 1, j3 - 1, m1] = (Bx[kp3 - 1, l3 - 1][:, :, cp.newaxis] * PEyx[ip3 - 1, j3 - 1, m1]) + (
                Ax[kp3 - 1, l3 - 1][:, :, cp.newaxis] * Hzdiffx[ip3 - 1, j3 - 1, m1])
        PEyx[ii3 - 1, jp3 - 1, m1] = (Bx[ki3 - 1, lp3 - 1][:, :, cp.newaxis] * PEyx[ii3 - 1, jp3 - 1, m1]) + (
                Ax[ki3 - 1, lp3 - 1][:, :, cp.newaxis] * Hzdiffx[ii3 - 1, jp3 - 1, m1])

        # 更新 PEyz 组件
        PEyz[ip3 - 1, j3 - 1, m1] = (Bz[kp3 - 1, l3 - 1][:, :, cp.newaxis] * PEyz[ip3 - 1, j3 - 1, m1]) + (
                Az[kp3 - 1, l3 - 1][:, :, cp.newaxis] * Hxdiffz[ip3 - 1, j3 - 1, m1])
        PEyz[ii3 - 1, jp3 - 1, m1] = (Bz[ki3 - 1, lp3 - 1][:, :, cp.newaxis] * PEyz[ii3 - 1, jp3 - 1, m1]) + (
                Az[ki3 - 1, lp3 - 1][:, :, cp.newaxis] * Hxdiffz[ii3 - 1, jp3 - 1, m1])

        # 更新 Ey 组件
        Ey[ip3 - 1, j3 - 1, m1] += Cc[kp3 - 1, l3 - 1][:, :, cp.newaxis] * (
                PEyx[ip3 - 1, j3 - 1, m1] - PEyz[ip3 - 1, j3 - 1, m1])
        Ey[ii3 - 1, jp3 - 1, m1] += Cc[ki3 - 1, lp3 - 1][:, :, cp.newaxis] * (
                PEyx[ii3 - 1, jp3 - 1, m1] - PEyz[ii3 - 1, jp3 - 1, m1])

        # 添加源脉冲到 Ey
        srci = np.array(srci)
        for v in range(maxsource):
            i = int(srci[0, (s1 - 1) * maxsource + v])
            j = int(srci[1, (s1 - 1) * maxsource + v])
            data[it, (s1 - 1) * maxsource + v]=Ey[i, j, v]


    return data
