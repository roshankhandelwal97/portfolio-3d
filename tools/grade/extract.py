import json, struct, sys, io
from PIL import Image
for name in sys.argv[1:] or ["smug_eyes", "grimace_eyes"]:
    b = open(f"site/models/{name}.glb", "rb").read()
    L = struct.unpack("<I", b[12:16])[0]; j = json.loads(b[20:20+L])
    bin_off = 20 + L + 8
    mat = j["materials"][0]
    ti = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    img = j["images"][j["textures"][ti].get("source", j["textures"][ti].get("extensions", {}).get("EXT_texture_webp", {}).get("source"))]
    bv = j["bufferViews"][img["bufferView"]]
    data = b[bin_off + bv.get("byteOffset", 0): bin_off + bv.get("byteOffset", 0) + bv["byteLength"]]
    im = Image.open(io.BytesIO(data)).convert("RGB"); im.save(f"grade/{name}_base.png"); print(name, im.size, img.get("mimeType"))
