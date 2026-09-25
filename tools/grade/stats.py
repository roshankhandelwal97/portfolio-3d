import numpy as np, json
from PIL import Image
def lin(a): return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
def load(n):
    a = np.asarray(Image.open(f"grade/{n}_base.png"), np.float32).reshape(-1, 3) / 255
    return lin(a)
out = {}
for n in ["smug_eyes", "grimace_eyes", "new"]:
    x = load(n); Y = x @ [0.2126, 0.7152, 0.0722]
    r, g, b = x.T
    hair = (Y < 0.03) & (Y > 0.002)
    skin = (Y > 0.12) & (Y < 0.8) & (r > g) & (g > b) & (r - b > 0.08)
    out[n] = {k: dict(mean=x[m].mean(0).tolist(), std=x[m].std(0).tolist(), frac=float(m.mean())) for k, m in [("hair", hair), ("skin", skin)]}
    print(n, {k: ([round(v, 4) for v in d["mean"]], round(d["frac"], 3)) for k, d in out[n].items()})
json.dump(out, open("grade/stats.json", "w"), indent=1)
