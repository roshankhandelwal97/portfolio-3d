import sys, json, numpy as np, cv2
import scipy.sparse as sp, scipy.sparse.linalg as spla
from PIL import Image
from scipy import ndimage as ndi

BOXES = {
    'smug':    [(140, 120, 560, 320), (900, 140, 1320, 330)],
    'grimace': [(120, 150, 510, 370), (840, 160, 1230, 380)],
    'worried': [(130, 130, 530, 370), (840, 130, 1240, 370)],
}
LID_DZ = 0.004
# Smug's irises are cut by the lids on both sides, which defeats the sclera-edge circle search.
IRIS_OVERRIDE = {'smug': [(418, 222, 82), (1172, 236, 82)]}
tag = sys.argv[1]
img = np.asarray(Image.open(f'{tag}_eyes_render.png').convert('RGB'))
buf = np.load(f'{tag}_eyes_buf.npz'); zb, fb = buf['zb'], buf['fb']
X0, Y1, S = float(buf['X0']), float(buf['Y1']), float(buf['S'])
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
H, Sat, Val = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255

def find_iris(sub_img, sclera, hint):
    v = cv2.cvtColor(sub_img, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    best = None
    ang = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    hh, ww = v.shape
    for r in range(55, 105, 2):
        for cy in range(hint[1] - 40, hint[1] + 41, 3):
            for cx in range(hint[0] - 90, hint[0] + 91, 3):
                xo = np.clip((cx + (r + 5) * np.cos(ang)).astype(int), 0, ww - 1)
                yo = np.clip((cy + (r + 5) * np.sin(ang)).astype(int), 0, hh - 1)
                xi = np.clip((cx + (r - 5) * np.cos(ang)).astype(int), 0, ww - 1)
                yi = np.clip((cy + (r - 5) * np.sin(ang)).astype(int), 0, hh - 1)
                on = sclera[yo, xo]
                if on.sum() < 12: continue
                score = ((v[yo, xo] - v[yi, xi]) * on).sum()
                if best is None or score > best[0]: best = (score, cx, cy, r)
    return best

eyes = []
for (bx0, by0, bx1, by1) in BOXES[tag]:
    sub = img[by0:by1, bx0:bx1]; sv, ss = Val[by0:by1, bx0:bx1], Sat[by0:by1, bx0:bx1]
    sclera = (sv > 0.72) & (ss < 0.30) & (fb[by0:by1, bx0:bx1] >= 0)
    lab, n = ndi.label(sclera); sizes = ndi.sum(sclera, lab, range(1, n + 1))
    sclera = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 400])
    ys, xs = np.where(sclera)
    hint = (int(xs.mean()), int(ys.mean()))
    ov = IRIS_OVERRIDE.get(tag)
    if ov:
        k = len(eyes); cx, cy, r = ov[k][0] - bx0, ov[k][1] - by0, ov[k][2]; score = 0.0
    else:
        score, cx, cy, r = find_iris(sub, sclera, hint)
    hh, ww = sclera.shape
    gy, gx = np.mgrid[0:hh, 0:ww]
    d = np.hypot(gx - cx, gy - cy)
    # Lids overhang the eyeball: inside the iris disk, the lid edge is the strongest depth drop per column.
    zz = zb[by0:by1, bx0:bx1]
    top = np.full(ww, -1); bot = np.full(ww, -1)
    for c in range(ww):
        rows = np.arange(max(3, cy - 110), max(4, cy - 4))
        drop = zz[rows - 3, c] - zz[rows + 3, c]
        k = np.argmax(drop)
        if drop[k] > LID_DZ: top[c] = rows[k] + 2
        rows = np.arange(min(hh - 5, cy + 4), min(hh - 4, cy + 110))
        if len(rows):
            rise = zz[rows + 3, c] - zz[rows - 3, c]
            k = np.argmax(rise)
            if rise[k] > LID_DZ: bot[c] = rows[k] - 2
    # Inside the iris disk a missing lid step means the iris edge itself bounds the opening.
    for c in range(max(0, cx - r), min(ww, cx + r + 1)):
        half = int(np.sqrt(max(r * r - (c - cx) ** 2, 0)))
        if top[c] < 0: top[c] = cy - half
        if bot[c] < 0: bot[c] = cy + half
    valid = (top >= 0) & (bot > top + 4)
    # Keep the contiguous run of lid columns that contains the iris or sclera.
    lab, n = ndi.label(valid)
    keep = np.unique(lab[np.where(sclera.any(0) | (np.abs(np.arange(ww) - cx) < r))[0]]); keep = keep[keep > 0]
    valid = np.isin(lab, keep)
    idx = np.where(valid)[0]
    top[idx] = ndi.median_filter(top[idx], 9); bot[idx] = ndi.median_filter(bot[idx], 9)
    inlid = valid[None, :] & (gy > top[None, :]) & (gy < bot[None, :])
    dark = sv < 0.45
    op = sclera | (inlid & ((d < r) | dark))
    op = ndi.binary_closing(op, iterations=3)
    op = ndi.binary_fill_holes(op)
    lab, n = ndi.label(op); sizes = ndi.sum(op, lab, range(1, n + 1)); op = lab == (np.argmax(sizes) + 1)
    for c in range(ww):
        rows = np.where(op[:, c])[0]
        if len(rows): op[rows.min():rows.max() + 1, c] = True
    # Eye openings are convex; recover iris pixels the lid-step search missed at the corners.
    hull = np.zeros_like(op, np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(np.stack(np.where(op)[::-1], 1).astype(np.int32)), 1)
    op = op | (ndi.binary_erosion(hull.astype(bool), iterations=2) & (d < r + 6))
    alpha = cv2.GaussianBlur(ndi.binary_erosion(op, iterations=1).astype(np.float32), (5, 5), 1.2)
    # clean sclera: inpaint the iris disk
    # Fill the iris hole from sclera pixels only; generic inpainting drags lash colour into the white.
    src = (sclera & (d > r + 3)).astype(np.float32)
    subf = sub.astype(np.float32)
    sig = 0.6 * r
    num = cv2.GaussianBlur(subf * src[..., None], (0, 0), sig); den = cv2.GaussianBlur(src, (0, 0), sig)
    fill = num / np.maximum(den, 1e-6)[..., None]
    hole = op & ~sclera
    hole = ndi.binary_dilation(hole, iterations=2) & op
    clean = subf.copy(); clean[hole] = fill[hole]
    # Harmonic fill: sclera pixels are fixed boundary, lid pixels are ignored so no lash colour bleeds in.
    # The sclera darkens toward the painted iris (baked occlusion), so a boundary-driven fill comes out grey.
    # Fit a smooth quadratic to the whole visible sclera instead and feather it over the iris edge.
    known = (src > 0) & (d > r + 12)
    # Vertical-only terms: smug's visible sclera is all on one side, so any x term extrapolates wildly.
    Xp = np.stack([np.ones_like(gy), gy / hh, (gy / hh) ** 2], -1).astype(np.float64)
    fitc = np.stack([np.linalg.lstsq(Xp[known], subf[..., k][known], rcond=None)[0] for k in range(3)], -1)
    smooth = Xp @ fitc
    near = cv2.GaussianBlur(ndi.binary_dilation(hole, iterations=10).astype(np.float32), (0, 0), 5)
    w_ = np.where(hole, 1.0, near)[..., None]
    clean = subf * (1 - w_) + smooth * w_
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3)[..., None]
    clean = np.clip(clean * (1 - soft) + cv2.GaussianBlur(clean, (0, 0), 4) * soft, 0, 255).astype(np.uint8)
    ref = np.median(cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY)[sclera & (d > r + 6)])
    zs = zb[by0:by1, bx0:bx1][op]
    eyes.append(dict(box=(bx0, by0, bx1, by1), cx=cx, cy=cy, r=r, score=float(score), alpha=alpha, clean=clean,
                     op=op, sub=sub, ref=float(ref), z=(float(zs.min()), float(zs.max()))))
    print(tag, 'eye', (bx0, by0), 'iris c=(%d,%d) r=%d' % (cx + bx0, cy + by0, r), 'opening px', int(op.sum()), 'z', eyes[-1]['z'], 'scleraRef', ref)

# debug overlay
dbg = img.copy()
for e in eyes:
    bx0, by0, bx1, by1 = e['box']
    cnt, _ = cv2.findContours(e['op'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(dbg[by0:by1, bx0:bx1], cnt, -1, (0, 255, 0), 1)
    cv2.circle(dbg, (e['cx'] + bx0, e['cy'] + by0), e['r'], (255, 0, 255), 1)
Image.fromarray(dbg).save(f'{tag}_extract_dbg.png')
np.save(f'{tag}_eyes.npy', np.array([{k: v for k, v in e.items()} for e in eyes], dtype=object), allow_pickle=True)
