import sys, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
tag = sys.argv[1]
d = np.load(f'{tag}_mesh.npz'); V, UV, F = d['V'], d['UV'], d['F']
X0, X1, Y0, Y1 = [float(a) for a in sys.argv[2:6]] if len(sys.argv) > 5 else (-0.30, 0.36, 0.06, 0.26)
S = 1500 / (X1 - X0)
Wd, Hd = int((X1 - X0) * S), int((Y1 - Y0) * S)
tri = V[F]
inb = ((tri[:, :, 0] > X0 - .02) & (tri[:, :, 0] < X1 + .02) & (tri[:, :, 1] > Y0 - .02) & (tri[:, :, 1] < Y1 + .02) & (tri[:, :, 2] > 0)).all(1)
import os
if os.path.exists(f'{tag}_lensmask.npy'): inb &= ~np.load(f'{tag}_lensmask.npy')
fids = np.where(inb)[0]
print('tris', len(fids))
zb = np.full((Hd, Wd), -1e9); uvb = np.zeros((Hd, Wd, 2)); fb = np.full((Hd, Wd), -1)
z2 = np.full((Hd, Wd), -1e9)  # second layer depth
for f in fids:
    p = tri[f]; px = (p[:, 0] - X0) * S; py = (Y1 - p[:, 1]) * S
    xa, xb = int(max(0, np.floor(px.min()))), int(min(Wd - 1, np.ceil(px.max())))
    ya, yb = int(max(0, np.floor(py.min()))), int(min(Hd - 1, np.ceil(py.max())))
    if xb < xa or yb < ya: continue
    gx, gy = np.meshgrid(np.arange(xa, xb + 1) + .5, np.arange(ya, yb + 1) + .5)
    d0 = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
    if abs(d0) < 1e-12: continue
    l0 = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / d0
    l1 = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / d0
    l2 = 1 - l0 - l1
    ins = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
    if not ins.any(): continue
    z = l0 * p[0, 2] + l1 * p[1, 2] + l2 * p[2, 2]
    uv = UV[F[f]]
    u = l0 * uv[0, 0] + l1 * uv[1, 0] + l2 * uv[2, 0]; v = l0 * uv[0, 1] + l1 * uv[1, 1] + l2 * uv[2, 1]
    yy, xx = np.where(ins); Y = yy + ya; Xx = xx + xa; zz = z[ins]
    cur = zb[Y, Xx]
    front = zz > cur
    # push old to second layer where replaced
    z2[Y[front], Xx[front]] = np.maximum(z2[Y[front], Xx[front]], cur[front])
    z2[Y[~front], Xx[~front]] = np.maximum(z2[Y[~front], Xx[~front]], zz[~front])
    zb[Y[front], Xx[front]] = zz[front]; uvb[Y[front], Xx[front], 0] = u[ins][front]; uvb[Y[front], Xx[front], 1] = v[ins][front]; fb[Y[front], Xx[front]] = f
tex = np.asarray(Image.open(f'{tag}_base.png'))
T = tex.shape[0]
tx = np.clip((uvb[..., 0] * T).astype(int), 0, T - 1); ty = np.clip(((1 - uvb[..., 1]) * T).astype(int), 0, T - 1)
col = tex[ty, tx]; col[fb < 0] = 0
Image.fromarray(col).save(f'{tag}_eyes_render.png')
gap = zb - z2; gap[(fb < 0) | (z2 < -1e8)] = 0
Image.fromarray((np.clip(gap / 0.03, 0, 1) * 255).astype(np.uint8)).save(f'{tag}_eyes_gap.png')
np.savez(f'{tag}_eyes_buf.npz', zb=zb, uvb=uvb, fb=fb, z2=z2, X0=X0, Y1=Y1, S=S)
print('done', Wd, Hd)
