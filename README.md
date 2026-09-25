# Roshan Khandelwal — portfolio

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

## Credits

- Cat: "Somali Cat Animated ver 1.2" by [DreamNoms](https://sketchfab.com/3d-models/somali-cat-animated-ver-12-e185c3fd92b64c32b4515a32b29252fc), CC BY 4.0 (recoloured)
- MacBook: "2021 Macbook Pro 14\" (M1 Pro / M1 Max)" by [akshatmittal](https://sketchfab.com/3d-models/2021-macbook-pro-14-m1-pro-m1-max-f6b0b940fb6a4286b18a674ef32af2d3), CC BY 4.0 (logo removed, recoloured)
- Plane flyby: [InspectorJ](https://commons.wikimedia.org/wiki/File:428086_inspectorj_airplane-boeing-flyby-right-to-left-a.wav), CC BY 4.0 (trimmed)
- Football kick: [Soccer kick effect](https://commons.wikimedia.org/wiki/File:Soccer_kick_effect.ogg), CC BY-SA 3.0 (trimmed)
- Cat meow: [Meow of a pleading cat](https://commons.wikimedia.org/wiki/File:Meow_of_a_pleading_cat.oga) , public domain
- Latest Barça result: ESPN public scoreboard API
