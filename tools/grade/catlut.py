import json, struct, io, numpy as np
from PIL import Image
b = open('site/models/cats/somali_cat_animated_ver_1.2.glb', 'rb').read()
L = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20+L]); off = 20 + L + 8
mat = next(m for m in j['materials'] if m.get('name') == 'SomaliTexture')
tex = j['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]
bv = j['bufferViews'][j['images'][tex['source']]['bufferView']]
som = np.asarray(Image.open(io.BytesIO(b[off+bv.get('byteOffset',0): off+bv.get('byteOffset',0)+bv['byteLength']])).convert('RGB'), np.float32) / 255
ref = np.asarray(Image.open('/Users/roshankhandelwal/Downloads/ChatGPT Image Sep 24, 2026, 03_02_14 PM.png').convert('RGB'), np.float32) / 255
def sat(a): mx = a.max(-1); return np.where(mx > 0, (mx - a.min(-1)) / np.maximum(mx, 1e-6), 0)
lum = lambda a: a @ np.array([0.299, 0.587, 0.114])
r = ref.reshape(-1, 3); r = r[sat(r) > 0.3]          # cat fur only, not the grey backdrop
s = som.reshape(-1, 3); s = s[(sat(s) > 0.2) | (lum(s) > 0.55)]
rl, sl = lum(r), lum(s)
order = np.argsort(rl); r, rl = r[order], rl[order]
lut = np.zeros((256, 3))
for i in range(256):
    q = (sl < (i + 0.5) / 255).mean()                      # percentile of this luminance in the model's fur
    k = int(np.clip(q, 0.002, 0.998) * (len(rl) - 1))
    lo, hi = max(0, k - 400), min(len(rl), k + 400)
    lut[i] = r[lo:hi].mean(0)
# No white or cream: every light entry keeps at least a soft-orange saturation.
import colorsys
for i in range(256):
    h, sa, v = colorsys.rgb_to_hsv(*np.clip(lut[i], 0, 1))
    h = min(h, 0.085) if sa > 0.05 else 0.075
    lut[i] = colorsys.hsv_to_rgb(h, max(sa, 0.5), min(v, 0.97))
Image.fromarray((np.clip(lut, 0, 1)[None] * 255).astype(np.uint8)).save('site/models/cats/fur_lut.png')
print('model fur lum p5/p50/p95', np.percentile(sl, [5, 50, 95]).round(2), 'ref', np.percentile(rl, [5, 50, 95]).round(2))
print('lut samples', (lut[[40, 90, 140, 190, 240]] * 255).round().astype(int).tolist())
