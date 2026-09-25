import sys, io, json, struct, numpy as np, trimesh
from PIL import Image
src, tag = sys.argv[1], sys.argv[2]
b = open(src,'rb').read(); L = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20+L])
binoff = 20 + L + 8
mat = j['materials'][0]; bci = j['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
bv = j['bufferViews'][j['images'][bci]['bufferView']]
img = Image.open(io.BytesIO(b[binoff+bv.get('byteOffset',0):binoff+bv.get('byteOffset',0)+bv['byteLength']])).convert('RGB')
print('tex', img.size)
img.save(f'eyes/{tag}_base.png')
sc = trimesh.load(src, process=False); m = list(sc.geometry.values())[0]
V = m.vertices; UV = m.visual.uv; N = m.vertex_normals
print('bounds', V.min(0), V.max(0))
T = np.asarray(img).astype(np.float32)/255; H, W = T.shape[:2]
px = np.clip((UV[:,0]*W).astype(int),0,W-1); py = np.clip(((1-UV[:,1])*H).astype(int),0,H-1)
C = T[py, px]
np.savez(f'eyes/{tag}_mesh.npz', V=V, UV=UV, N=N, F=m.faces)
print('saved')
