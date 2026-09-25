import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { DecalGeometry } from 'three/addons/geometries/DecalGeometry.js';

// The painted eyes straddle UV seams, so the iris is re-drawn in model space: each GLB carries an atlas with the
// eye whites (iris removed) plus an iris disc, and per-eye bounds in the model's front-projected XY.
export const look = { value: new THREE.Vector2() };
function addEyes(root, atlas, eyes, grade) {
  const invRoot = { value: new THREE.Matrix4() };
  const u = {
    uEyeAtlas: { value: atlas }, uInvRoot: invRoot, uLook: look,
    uBox: { value: eyes.map((e) => new THREE.Vector4(...e.box)) },
    uBoxRect: { value: eyes.map((e) => new THREE.Vector4(...e.boxRect)) },
    uIrisC: { value: eyes.map((e) => new THREE.Vector2(...e.irisC)) },
    uIrisH: { value: eyes.map((e) => e.irisH) },
    uIrisRect: { value: eyes.map((e) => new THREE.Vector4(...e.irisRect)) },
    uRange: { value: eyes.map((e) => new THREE.Vector2(...e.range)) },
    uZ: { value: eyes.map((e) => new THREE.Vector2(...e.z)) },
    uFront: { value: 1 },
    uGradeOn: { value: grade ? 1 : 0 },
    uGradeSkin: { value: new THREE.Vector3(...(grade?.skin ?? [1, 1, 1])) },
    uGradeHair: { value: new THREE.Vector3(...(grade?.hair ?? [1, 1, 1])) },
  };
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, u);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vEyeW;\nvarying vec3 vEyeN;')
        .replace('#include <project_vertex>', `#include <project_vertex>
          vEyeW = (modelMatrix * vec4(transformed, 1.0)).xyz;
          vEyeN = mat3(modelMatrix) * objectNormal;`);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
          varying vec3 vEyeW; varying vec3 vEyeN;
          uniform sampler2D uEyeAtlas; uniform mat4 uInvRoot; uniform vec2 uLook;
          uniform vec4 uBox[2]; uniform vec4 uBoxRect[2]; uniform vec2 uIrisC[2]; uniform float uIrisH[2];
          uniform vec4 uIrisRect[2]; uniform vec2 uRange[2]; uniform vec2 uZ[2];
          uniform float uGradeOn; uniform vec3 uGradeSkin; uniform vec3 uGradeHair; uniform float uFront;
          float eyeMask = 0.0;`)
        // The normal map still carries the relief of the sculpted iris, which reads as a hollow once the drawn
        // iris moves off it; inside the eye, drop that relief and ease the normal toward the viewer.
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
          normal = normalize(mix(normal, normalize(mix(nonPerturbedNormal, vec3(0.0, 0.0, 1.0), 0.45)), eyeMask));`)
        .replace('#include <map_fragment>', `#include <map_fragment>
          {
            vec3 ep = (uInvRoot * vec4(vEyeW, 1.0)).xyz;
            vec3 en = normalize(mat3(uInvRoot) * vEyeN);
            for (int i = 0; i < 2; i++) {
              if (ep.z < uZ[i].x || ep.z > uZ[i].y || en.z <= 0.0) continue;
              vec2 q = vec2((ep.x - uBox[i].x) / (uBox[i].z - uBox[i].x), (uBox[i].w - ep.y) / (uBox[i].w - uBox[i].y));
              if (any(lessThan(q, vec2(0.0))) || any(greaterThan(q, vec2(1.0)))) continue;
              vec4 sc = texture(uEyeAtlas, mix(uBoxRect[i].xy, uBoxRect[i].zw, q));
              vec2 c = uIrisC[i] + uLook * uRange[i];
              vec2 iq = vec2(ep.x - c.x, c.y - ep.y) / (2.0 * uIrisH[i]) + 0.5;
              vec4 ir = vec4(0.0);
              if (all(greaterThan(iq, vec2(0.0))) && all(lessThan(iq, vec2(1.0))))
                ir = texture(uEyeAtlas, mix(uIrisRect[i].xy, uIrisRect[i].zw, iq));
              float shade = mix(0.7, 1.0, smoothstep(0.0, 0.9, sc.a));
              // Whites toned down to a warm off-white and irises deepened, so the eyes don't read as bright CG.
              vec3 col = mix(sc.rgb * vec3(0.84, 0.8, 0.76), ir.rgb * shade * 0.62, ir.a);
              // The overlay is projected along the model's z axis and smears once the head turns well away from the
              // camera; uFront fades it out so the sculpt's own painted eyes show in profile.
              diffuseColor.rgb = mix(diffuseColor.rgb, col, sc.a * uFront);
              eyeMask = max(eyeMask, sc.a * uFront);
            }
            // Each generation came out with its own colour balance; per-channel gains (measured offline on the
            // skin and hair of both textures) pull this head onto the reference palette. Neutral pixels — teeth,
            // eye whites, glasses — are left alone.
            if (uGradeOn > 0.5) {
              vec3 c = diffuseColor.rgb;
              float y = dot(c, vec3(0.2126, 0.7152, 0.0722));
              float mx = max(c.r, max(c.g, c.b));
              float sat = mx > 0.0 ? (mx - min(c.r, min(c.g, c.b))) / mx : 0.0;
              vec3 gain = mix(uGradeHair, uGradeSkin, smoothstep(0.03, 0.15, y));
              diffuseColor.rgb = c * mix(vec3(1.0), gain, smoothstep(0.15, 0.4, sat));
            }
          }`);
    };
    o.material.customProgramCacheKey = () => 'eyes';
  });
  return { invRoot, front: u.uFront };
}

// Other heads re-graded onto the smug head's palette (smug mean / grimace mean, linear RGB, from grade/stats.py).
const GRADES = {
  'models/grimace_eyes.glb': { skin: [0.9012, 0.7903, 0.7347], hair: [0.3194, 0.2608, 0.24] },
};
// Applied on top of every head's grade: a slightly deeper skin tone than the generator produced (linear gains).
const SKIN_TONE = [0.7, 0.66, 0.64];
function gradeFor(url) {
  const g = GRADES[url] ?? { skin: [1, 1, 1], hair: [1, 1, 1] };
  return { skin: g.skin.map((v, i) => v * SKIN_TONE[i]), hair: g.hair };
}

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
async function loadHead(url, neckY) {
  const gltf = await loader.loadAsync(url);
  const root = gltf.scene;
  const meta = root.userData.eyes;
  const atlas = await gltf.parser.getDependency('texture', meta.texture);
  atlas.colorSpace = THREE.SRGBColorSpace;
  const { invRoot, front } = addEyes(root, atlas, meta.eyes, gradeFor(url));
  const box = new THREE.Box3().setFromObject(root);
  const c = box.getCenter(new THREE.Vector3());
  root.position.set(-c.x, -box.max.y + 0.95 - neckY, -c.z);
  return { root, invRoot, front };
}

// Placement is an angle around the head (0 = straight at the face) and a height; the decal is projected onto
// whatever surface a ray from that direction hits first. A per-head key (e.g. `grimace`) overrides the placement
// where the two sculpts differ.
export const STICKERS = [
  { file: '00-india.png', yaw: -18, y: 0.34, size: 0.17, tilt: -6, grimace: { y: 0.42 } },
  { file: '02-nmims.png', yaw: -56, y: -0.04, size: 0.19, tilt: -6 },
  { file: '01-mumbai.png', yaw: -92, y: -0.44, size: 0.21, tilt: 8 },
  { file: '05-usa.png', yaw: 26, y: 0.28, size: 0.12, tilt: 8, grimace: { y: 0.37 } },
  { file: '05b-syracuse.png', yaw: 56, y: -0.02, size: 0.20, tilt: 6 },
  { file: '06-chemistry.png', yaw: 70, y: -0.34, size: 0.14, tilt: -8 },
  { file: '06b-darkstore.png', yaw: 112, y: -0.14, size: 0.15, tilt: 8 },
  { file: '07-biztrip.png', yaw: 0, y: -0.50, size: 0.42, tilt: -6, grimace: { y: -0.42 } },
  { file: '03-accenture.png', yaw: -40, y: -0.22, size: 0.26, tilt: -10 },
  { file: '09-cat.png', yaw: 205, y: -0.32, size: 0.20, tilt: 12 },
  { file: '08-fcb.png', yaw: 150, y: -0.34, size: 0.16, tilt: -8 },
];
const texLoader = new THREE.TextureLoader();
const stickerTex = Object.fromEntries(await Promise.all(STICKERS.map(async (st) => {
  const t = await texLoader.loadAsync(`stickers/${st.file.includes('.') ? st.file : st.file + '.svg'}`);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return [st.file, t];
})));

// DecalGeometry clips every triangle of the mesh it is given; handing it only the triangles near the hit keeps
// sticker setup from scanning the whole 200k-triangle head once per sticker.
function localPatch(mesh, point, size, normal) {
  const pos = mesh.geometry.attributes.position, nor = mesh.geometry.attributes.normal, idx = mesh.geometry.index;
  const local = mesh.worldToLocal(point.clone());
  // Keep only surface facing the same way as the hit and lying close to it along the normal, so strands of hair
  // hovering in front of the skin don't get a piece of the sticker printed on them.
  const nLocal = normal.clone().transformDirection(mesh.matrixWorld.clone().invert()).normalize();
  const fa = new THREE.Vector3(), fb = new THREE.Vector3(), fc = new THREE.Vector3(), fn = new THREE.Vector3();
  const s = new THREE.Vector3().setFromMatrixScale(mesh.matrixWorld);
  const r2 = (size / Math.min(s.x, s.y, s.z)) ** 2;
  const P = [], N = [], v = new THREE.Vector3();
  const count = idx ? idx.count : pos.count;
  for (let i = 0; i < count; i += 3) {
    const a = idx ? idx.getX(i) : i;
    if (v.fromBufferAttribute(pos, a).distanceToSquared(local) > r2) continue;
    const b = idx ? idx.getX(i + 1) : i + 1, c = idx ? idx.getX(i + 2) : i + 2;
    fa.fromBufferAttribute(pos, a); fb.fromBufferAttribute(pos, b); fc.fromBufferAttribute(pos, c);
    fn.subVectors(fc, fb).cross(fa.clone().sub(fb)).normalize();
    if (fn.dot(nLocal) < -0.1) continue;
    const off = fa.clone().add(fb).add(fc).multiplyScalar(1 / 3).sub(local).dot(nLocal);
    if (off > 0.02) continue;
    for (let k = 0; k < 3; k++) {
      const j = idx ? idx.getX(i + k) : i + k;
      P.push(pos.getX(j), pos.getY(j), pos.getZ(j)); N.push(nor.getX(j), nor.getY(j), nor.getZ(j));
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
  const m = new THREE.Mesh(g); m.matrixWorld.copy(mesh.matrixWorld);
  return m;
}

function addStickers(root, headKey) {
  const meshes = []; root.traverse((o) => { if (o.isMesh) meshes.push(o); });
  root.updateWorldMatrix(true, true);
  const ray = new THREE.Raycaster(), helper = new THREE.Object3D();
  const centre = new THREE.Box3().setFromObject(root).getCenter(new THREE.Vector3());
  STICKERS.forEach((base) => {
    const st = { ...base, ...(base[headKey] || {}) };
    const a = THREE.MathUtils.degToRad(st.yaw);
    const target = new THREE.Vector3(centre.x, st.y, centre.z);
    const origin = target.clone().add(new THREE.Vector3(Math.sin(a) * 4, 0, Math.cos(a) * 4));
    ray.set(origin, target.clone().sub(origin).normalize());
    const hit = ray.intersectObjects(meshes, false)[0];
    if (!hit) return;
    const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
    helper.position.copy(hit.point); helper.lookAt(hit.point.clone().add(n));
    helper.rotateZ(THREE.MathUtils.degToRad(st.tilt));
    const img = stickerTex[st.file].image, aspect = img.height / img.width;
    const decal = new THREE.Mesh(
      new DecalGeometry(localPatch(hit.object, hit.point, st.size, n), hit.point, helper.rotation, new THREE.Vector3(st.size, st.size * aspect, Math.max(0.25, st.size * 1.2))),
      new THREE.MeshStandardMaterial({ map: stickerTex[st.file], bumpMap: stickerTex[st.file], bumpScale: 1.2,
        transparent: true, alphaTest: 0.02, roughness: 1, metalness: 0, envMapIntensity: 0.35,
        depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 }));
    decal.userData.sticker = st.file;
    STICKER_MESHES.push(decal);
    hit.object.attach(decal);
  });
}

// Every placed sticker, so the page can pull the current chapter's patch onto the sharp layer.
export const STICKER_MESHES = [];

export const HEADS = { smug: 'models/smug_eyes.glb', grimace: 'models/grimace_eyes.glb' };

// Sticker heights are world-space, so heads must sit in the pivot (at neckY) before stickers are projected.
export async function loadHeads(pivot) {
  const entries = await Promise.all(Object.entries(HEADS).map(async ([key, url]) => {
    const h = await loadHead(url, pivot.position.y);
    pivot.add(h.root);
    pivot.updateWorldMatrix(true, true);
    addStickers(h.root, key);
    return [key, h];
  }));
  return Object.fromEntries(entries);
}
