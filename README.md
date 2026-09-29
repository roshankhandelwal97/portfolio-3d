# [Roshan Khandelwal — portfolio](https://roshan-khandelwal-eight.vercel.app/)

A scroll-driven 3D portfolio: a stylized bust covered in embroidered patches that turns to each chapter of the story,
with cursor-tracking eyes, an orbiting plane, a wandering cat and a kickable football.

Plain static site — `index.html` + `head.js`, three.js from a CDN, no build step.

```sh
python3 -m http.server 8000   # then open http://localhost:8000
```

## Layout

- `index.html` — page, chapters, scroll camera, scene extras (plane, molecules, boarding passes, phone, ball, cat)
- `head.js` — head loading, eye tracking, colour grading, sticker placement
- `models/` — web-optimised glTF (meshopt + WebP)
- `stickers/` — patch artwork
- `tools/` — offline scripts used to prepare the eye-tracking data and colour grades

## The face models

The three faces (smug, grimace, whistle) are generated, not scanned.

**Tools.** Images: ChatGPT. Image-to-3D: [3D AI Studio](https://www.3daistudio.com), which runs several generators in
one place. We tried Hunyuan3D, Tripo and Rodin, and used **Meshy 7.1** for all three faces. Post-processing: [glTF Transform](https://gltf-transform.dev) and the
scripts in `tools/`.

To make a new one:

1. **Stylised reference.** Turn a front photo into a Pixar-style head-and-shoulders bust with ChatGPT (image generation):
   same glasses, beard and black t-shirt, plain grey background, front view, no text.
2. **Expression.** Give ChatGPT that bust back with: *"Keep this exact character identical — same face, identity, hair,
   beard, rimless glasses, black t-shirt, style, framing, lighting and plain grey background. Change only the
   expression to …"*. Exaggerate it so it survives the jump to 3D.
3. **3D.** [3D AI Studio](https://www.3daistudio.com) → Image to 3D → All models → **Meshy 7.1**, single image. Mesh: Ultra 2K, Triangle topology.
   Generate Textures on, PBR on, texture quality Ultra. Download the GLB.
4. **Web-optimise.**
   ```sh
   npx @gltf-transform/cli@4 optimize in.glb models/<face>.glb --compress meshopt --texture-compress webp \
     --texture-size 2048 --simplify true --simplify-ratio 0.12 --simplify-error 0.0005
   ```
5. **Eye tracking.** `tools/eyes` (`probe` → `raster` → `extract` → `build`) bakes the eye outlines and an iris atlas
   into `models/<face>_eyes.glb`. The scripts are tuned per face (eye boxes are hard-coded), so expect to adjust them.
6. **Colour match.** `tools/grade` measures skin and hair against the smug face; add the gains to `GRADES` in `head.js`.
7. **Wire it in.** Add the file to `HEADS` in `head.js` and to `FACE_AT` in `index.html` (the yaw at which it swaps in,
   always while the back of the head faces the camera). Stickers need no work: they're placed on the first face and
   reused on the others.

## Credits

- Faces: generated with ChatGPT and Meshy 7.1 (via 3D AI Studio) from photos of me (see [The face models](#the-face-models))
- Aloo's photo: my own cat
- Cat: "Somali Cat Animated ver 1.2" by [DreamNoms](https://sketchfab.com/3d-models/somali-cat-animated-ver-12-e185c3fd92b64c32b4515a32b29252fc), CC BY 4.0 (recoloured)
- MacBook: "2021 Macbook Pro 14\" (M1 Pro / M1 Max)" by [akshatmittal](https://sketchfab.com/3d-models/2021-macbook-pro-14-m1-pro-m1-max-f6b0b940fb6a4286b18a674ef32af2d3), CC BY 4.0 (logo removed, recoloured)
- Plane flyby: [InspectorJ](https://commons.wikimedia.org/wiki/File:428086_inspectorj_airplane-boeing-flyby-right-to-left-a.wav), CC BY 4.0 (trimmed)
- Football kick: [Soccer kick effect](https://commons.wikimedia.org/wiki/File:Soccer_kick_effect.ogg), CC BY-SA 3.0 (trimmed)
- Cat meow: [Meow of a pleading cat](https://commons.wikimedia.org/wiki/File:Meow_of_a_pleading_cat.oga) , public domain
- Latest Barça result: ESPN public scoreboard API
