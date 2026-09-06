# Geneesi - briefing for a new agent

Read CLAUDE.md first (its four rules and the GLSL comment rule are binding). This file is the
project context that the code and git history do not tell you. Last updated 2026-09-06.

## What this is

A single-file Babylon.js v9 / WebGL2 molecular viewer of the thylakoid membrane (photosynthesis):
PSII, cytochrome b6f, PSI, ATP synthase and the other complexes as mol2 models, a lipid bilayer
built from templates, free water / protons / NADP, plastoquinone and plastocyanin shuttles that
travel between binding sites, photons that hit chlorophylls. UI text is Finnish. The look is
"painterly": a posterising comic-book post-process with ink outlines.

- Everything is in `index.html` (about 10 600 lines). There is no build step, no bundler, no
  framework. Edit the file directly.
- Deploy = `git push origin main`. GitHub Pages serves it as geneesi.com (the `CNAME` file).
- Models: the `*.mol2` files in the root. `Chlorophyll.mol` is the 2D structural formula.
- `PERFORMANCE.md` (Finnish): the page must run on the discrete GPU. Never fix a GPU problem by
  editing the registry or OS settings - the owner forbade it. The GPU name is shown bottom-right.
- `smooth.html` is an old experiment, not part of the site.
- Language of the owner: Finnish, messages often in fast informal English with typos. They
  test on their own machine and describe what they see. Ask when the ask is ambiguous.

## Working loop that has proven reliable

1. Edit `index.html` with a Python script (exact-string replace with a uniqueness assert, write
   back with `newline=''` so CRLF is preserved). Short edits via a Bash heredoc, long ones as a
   script in the scratchpad. Use Windows paths inside Python.
2. Syntax check: extract every inline `<script>` block (no `src=`) to `chk.js` and run
   `node --check`. Also scan GLSL strings for a `;` inside a comment (Babylon's preprocessor
   splits on `;` - a semicolon in a shader comment silently kills the material).
3. Preview: the Browser pane dev server is `python -m http.server 8777`
   (`.claude/launch.json`, name `geneesi`). Reload with a cache-busting query.
4. Verify in the page with `javascript_tool`: the scene is
   `BABYLON.EngineStore.LastCreatedScene`, the camera is `scene.getCameraByName('cam')`
   (`scene.activeCamera` may be the selection-mask camera - do not use it). The hidden pane
   throttles timers, so patch `window.setTimeout` through a MessageChannel before waiting for
   the chunked build. For deterministic tests: `engine.stopRenderLoop()`, force
   `engine._deltaTime = 16.7`, call `scene.render()` yourself, then restart the loop.
   Debug hooks on `window`: `__foot` (protein footprint grid), `__sites` (shuttle sites and
   occupancy), `__photons`.
5. Commit with a one-line descriptive message and push. The owner wants each change deployed.

## Architecture in one screen

- Atoms are rendered as thin instances. Thin-instance buffers live on the GEOMETRY: a `clone()`
  shares geometry, so call `makeGeometryUnique()` before giving a clone its own instances.
- Level of detail is one derived set of radii, `deriveLod()`: `gCrisp` (full atoms with
  orbitals, default 132), `gMega` (membrane drawn as a textured slab past this, default 600),
  `gMemBlend` (blend band, 60). Membrane and proteins use the SAME distances by design.
- The membrane is gathered per block around the camera into near/far streams with per-template
  caps; lipids under a protein's footprint (`buildProtFoot()`, a grid over the membrane plane,
  flood-filled from the border) are never drawn.
- The far membrane slab is a BOX as thick as the bilayer (2 x ySpan, about 46 units) with a procedural
  disc grain at half the lipid pitch. Across the blend band the shader cuts away the half facing the
  camera so the thinned lipids drawn there are never buried inside it. Its darkness is the dev slider
  'laatan tummuus' (gSlabDark, default 18 percent below the lipids' mean colour).
- Proteins have collision shells (`insideShell`, `camInsideModel`); free molecules bounce in a
  container box; protons pass ATP synthase only from the rotor side and spin the rotor.
- Shuttles: model clones (`MAX_MODELS` 48), one occupant per binding site (`siteOcc`), dock in
  contact with the host (`contact()`), wander on the way. Plastoquinone stays in the membrane
  plane, plastocyanin below the lipid layer.
- Photons: a camera-facing ribbon per photon drawn by `beamVertexShader` /
  `beamFragmentShader` (additive, no depth write). The painterly posteriser bands any bright
  gradient, so beam intensities are kept under its top level. Six fixed colours - the owner
  rejected rainbow tints.
- A BONDED hydrogen's 1s is an ellipsoid leaning into its bond (`h1sMat`, H_LONG 1.7, H_SHIFT 0.55 of
  the sphere's matrix scale), everywhere: protein atoms, lipid templates, free water and the atom card.
  Outlines and the free/lipid fills copy the drawn matrices, so they follow automatically.
- Free molecules spin (analytic, in the WATERBOX vertex path): angle = per-molecule random mix of the
  ANALYTIC bounced coordinates, so every wall bounce changes the spin. The hash is lowbias32 (`hsh` in
  GLSL, `hsh`/`spinS` in JS) so the CPU mirrors it bit for bit: the water orbital loop, the free
  picker, the trackers and the free-orbital placer all compose the same rotation (`spinAt`). Any new
  CPU code that places something on a free molecule MUST apply it too. Bouncing proteins re-roll their
  tumble on collision.
- Free-species orbitals: `freeOrb(nm, F, core, bond, frameOf, CAP)` is the shared placer, `linFrame`
  (CO2, O2) and `rigidFrame` (NADP) the frame providers, `rigidOrbSet(model)` builds a canonical lobe
  set from any parsed model's atoms and bonds. NADP is capped at the 160 nearest molecules.
- The scene is TWO rows deep: the 14 complexes/proteins of MODELS are cloned into a second row at
  z = +410 (after the shuttle clones, same `clone()` path), 51 models in all, MAX_MODELS 80 (the shaders
  declare modelXform[80] - keep them in step). DUP_ROWS (URL ?rows=0/1/2 overrides) - two extra rows
  put the JS heap at 4.6 GB against Chrome's 4 GB limit and the renderer died, one row sits at 3.3 GB.
  Every atom instance carries CPU-side buffers, so a full set costs about 1.3 GB - do not add models
  without measuring `performance.memory`. Only the first of a label drives the special cases (ATP
  rotor, shuttle sites, PSII gizmo). The particle box spans the whole membrane footprint (gMemFootX/Z)
  and the free-species counts scale with its volume via FILL (cap 3x, protons 2x) - the molecule id
  bases (MOLBASE) and the id texture size follow the counts. Build time 20-30 s, so a probe must wait.
- The membrane slab tier is OFF by default (`gSlabLod`, dev button 'laatta-LoD'): lipids at every
  distance, no sheet wrap, slab hidden. The protein hull handover still uses memR.
- Lighting: key light with a depth darkening by distance past the orbit pivot (`gDepthK`,
  `gDepthLo`). Chlorophylls are green, carotenoids orange, by ETC cofactor type.
- Camera: ArcRotate. The wheel has an ABSOLUTE maximum step `gZoomMax` (60 units per notch), a
  deterministic 10..100 percent ramp over the first ten notches of a gesture (400 ms chain
  window), pivots at what is under the cursor, and bleeds inertially. Never make the step a
  fraction of a distance - the owner rejected that twice.
- Selection follows atoms on moving models (`followModelAtom`); you cannot select a protein
  you are inside. Dev switches: selections on/off, photons on/off.
- Dev mode panel: every tunable has a slider with a reset, and the current slider values are
  meant to be the shipped defaults (quality 2.01x, crisp 132, mega 600, blend 60, pan 0.21x,
  rotate 155 deg/s, vignette 1.00 / 40). Adaptive quality back-off was removed on request.

## Pitfalls already paid for

- `hash2` overflowed float64 until `Math.imul` was used; rotamer picks were all 0.
- Sway phase must be seeded from the lipid origin, or some lipids lose their vdW spheres.
- ETC group centroids are already normalised - do not divide by n again.
- `LinesMesh` with vertex colours drew nothing and could kill the render loop.
- ArcRotate `setTarget` is a no-op when the target is unchanged; nudge it in tests.
- Per-frame allocations in `rebuildModelXform` caused rotation lag spikes; it uses
  preallocated matrices now. Keep hot paths allocation-free.
- A 60-frame synchronous test loop exceeds the 400 ms wheel chain window; space notches by
  three frames.

## Owner's taste, learned the hard way

Simplest thing that works. No abstractions they did not ask for. Do not touch unrelated code.
Visuals: Hollywood-grade, soft, no hard edges, no "childish" arcs; they will say when something
looks flat or jagged. When they say "all good?" check again - twice it was a real bug.

## Where things stand (2026-09-06, late evening)

Last commits, in order: a8d37e2 (video sky + zoom-out-from-centre), then the one carrying this note:
video sky REMOVED again, `Comp 1_1.mp4` deleted (still in git history), the flat dark-green quad is the
background, zoom-out-from-centre kept, and the nucleus fix below.

**Nuclei missing at certain angles - fixed, verify with the owner.** All-atom nuclei (`nucMatG`,
rendering group 1) do not write depth and are depth-TESTED with a bias toward the camera (`NUC_BIAS`
2 units) so they beat their own orbital lobes. The bias was clamped to HALF the view depth, so any atom
nearer than 4 units got less than the full bias and at 2 units only half - less than its own lobes
reach - and its nucleus vanished. Which atoms are that close changes as you turn, hence "at certain
angles". The clamp now stops at the near plane instead (read off the projection matrix in the imp
fragment shader). A remaining, smaller effect: a NEIGHBOUR's lobe or glass shell more than 2 units in
front of a nucleus still hides it, because every lobe and shell writes depth (`realAlpha()` sets
`forceDepthWrite`). If the owner still sees missing nuclei, raise `NUC_BIAS` toward 4-5 and check.

**Lag "a couple of commits ago" - two suspects, not yet confirmed with the owner:** the 1080p video
texture uploaded every frame (gone now), and the adaptive supersample back-off removed on request in
8c83dcf - the page used to lower its render scale quietly when slow, now it stays at the 2.01x quality
setting whatever happens. If it still lags after this commit, the quality slider is the lever.
