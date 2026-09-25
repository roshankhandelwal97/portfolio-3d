import sys, io, json, struct, numpy as np, cv2
from PIL import Image

tag, src_glb, dst_glb = sys.argv[1], sys.argv[2], sys.argv[3]
E = np.load(f'{tag}_eyes.npy', allow_pickle=True)
G = np.load('grimace_eyes.npy', allow_pickle=True)  # grimace irises are fully visible, so both heads use them
buf = np.load(f'{tag}_eyes_buf.npz'); zb = buf['zb']
X0, Y1, S = float(buf['X0']), float(buf['Y1']), float(buf['S'])

AW, AH = 1024, 512
atlas = np.zeros((AH, AW, 4), np.uint8)
srgb2lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
eyes = []
for i, e in enumerate(E):
    bx0, by0, bx1, by1 = e['box']
    h, w = e['alpha'].shape
    ox, oy = i * 512 + 4, 4
    atlas[oy:oy + h, ox:ox + w, :3] = e['clean']
    atlas[oy:oy + h, ox:ox + w, 3] = np.clip(e['alpha'] * 255, 0, 255).astype(np.uint8)
    g = G[i]; rg = g['r']; half = rg + 2
    crop = g['sub'][g['cy'] - half:g['cy'] + half, g['cx'] - half:g['cx'] + half]
    yy, xx = np.mgrid[0:2 * half, 0:2 * half] + 0.5
    dd = np.hypot(xx - half, yy - half)
    ia = np.clip(rg - dd + 0.5, 0, 1)
    ix, iy = i * 256 + 4, 260
    atlas[iy:iy + 2 * half, ix:ix + 2 * half, :3] = crop
    atlas[iy:iy + 2 * half, ix:ix + 2 * half, 3] = (ia * 255).astype(np.uint8)
    op = e['op']; ys, xs = np.where(op)
    cxp, cyp = xs.mean() + bx0, ys.mean() + by0
    halfW = (xs.max() - xs.min()) / 2
    r = e['r']
    zs = zb[by0:by1, bx0:bx1][op]
    ref = float(srgb2lin(e['ref'] / 255.0) * 1.0)
    eyes.append(dict(
        box=[X0 + bx0 / S, Y1 - by1 / S, X0 + bx1 / S, Y1 - by0 / S],
        boxRect=[ox / AW, oy / AH, (ox + w) / AW, (oy + h) / AH],
        irisC=[X0 + (cxp + .5) / S, Y1 - (cyp + .5) / S],
        irisH=(r / S) * half / rg,
        irisRect=[ix / AW, iy / AH, (ix + 2 * half) / AW, (iy + 2 * half) / AH],
        range=[max(0.15 * r, 0.6 * (halfW - 0.55 * r)) / S, 0.22 * r / S],
        z=[float(zs.min()) - 0.015, float(zs.max()) + 0.01],
        ref=ref))
Image.fromarray(atlas).save(f'{tag}_atlas.png', optimize=True)
png = open(f'{tag}_atlas.png', 'rb').read()
print(tag, 'atlas KB', len(png) // 1024)
print(json.dumps(eyes, indent=1)[:900])

b = open(src_glb, 'rb').read()
L = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + L])
binlen = struct.unpack('<I', b[20 + L:24 + L])[0]; binc = bytearray(b[28 + L:28 + L + binlen])
while len(binc) % 4: binc.append(0)
off = len(binc); binc += png
while len(binc) % 4: binc.append(0)
j['buffers'][0]['byteLength'] = len(binc)
j['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': len(png)})
j['images'].append({'mimeType': 'image/png', 'bufferView': len(j['bufferViews']) - 1})
j['samplers'].append({'magFilter': 9729, 'minFilter': 9729, 'wrapS': 33071, 'wrapT': 33071})
j['textures'].append({'sampler': len(j['samplers']) - 1, 'source': len(j['images']) - 1})
j['scenes'][0]['extras'] = {'eyes': {'texture': len(j['textures']) - 1, 'eyes': eyes}}
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(binc)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(binc)) + b'BIN\x00' + bytes(binc)
open(dst_glb, 'wb').write(out)
print('wrote', dst_glb, len(out) // 1024, 'KB')
