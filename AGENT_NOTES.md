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
- Protein atom thinning is by PROJECTED size (`protFrac`: full while a 1.7-radius atom is 1.5 px or more,
  then falling with the square, floor 1/16), never by fixed distance. The 1/16 'megacheap' step past
  memR is part of the slab tier and is off with it (`gSlabLod`).
- The membrane slab tier is OFF by default (`gSlabLod`, dev button 'laatta-LoD'): lipids at every
  distance, no sheet wrap, slab hidden. The protein hull handover still uses memR.
- Free ATP, ADP and Pi (1000 each, stroma) are rigid free species. ADP is carved out of the real NADP
  model by fixed atom indices (`adpFromNadp`: adenosine + both pyrophosphate phosphates, file bonds kept),
  ATP adds a gamma phosphate tetrahedrally on O5D, Pi is the spawn tool's PO4 tetrahedron (`MOL_BUILD`,
  moved above the free-species block with `reachOf`) with bonds inferred by distance. The straight-line
  cartoon is only the fallback if nadph.mol2 is missing. `RIGID_FREE` lists every rigid species for the picker, the
  trackers and the collision list (`gSpecies`). Each new species needs an id base in MOLBASE.
- UI layout: a full-width top pill row (`#toplist`, 24 pills in `PILLS` as [name, points], every one 0,5, RIGHT-click flies the camera to the thing via `PILL_GOTO` / `window.gPillFly(name)` - proteins by model label, cofactors by ETC residue type, atoms by element in a named model, free species and photons through `window.__freeNearest` / `window.__photonNearest`, wrapping, `.pill.on` =
  green, state in `window.gTopToggles`, no other behaviour yet) with a score card (`#scorebox`, 'Pisteet n', no total
  = the sum of the points of the pills that are on, in half-point steps (0,5 - 2,5), no dots,
  `window.updateScore`) and a plain 10-minute countdown card (`#timerbox`, stops at 0:00 and turns red, click = reset) stacked above the controller picture and a bottom-right dock (`#btndock`) holding the gear
  (`settings-btn`), fullscreen, the speed slider and the GPU badge. The toggle buttons live in the gear's
  `settings-menu`, re-anchored at the end of startup to open UPWARD above the dock, right-aligned. The
  dev panel is height-capped to stay clear of the dock.
- Gamepad (DualShock, standard mapping): polled every frame, EVERY connected pad merged (largest deflection
  per axis, largest value per button - with DS4Windows the physical pad is listed dead next to its virtual
  Xbox pad, so taking the first pad broke the right stick), drives the keyboard's own flags edge-
  triggered (left stick A/D + W/S, right stick arrows, L1/R1 = Q/E zoom, L2/R2 = M/N roll (keyboard N/M, R and F are free)). The picture
  bottom-left is ALWAYS shown: controls.png as the base with left/right/L1/L2/R1/R2.png stacked on it as
  transparent highlight layers (the owner's files, source kontrollit.psd), each visible while its control
  is in use, any number at once. `window.__pollPad` is the poll.
- Clocks: `gWaveT` (uniform `uT`) is the sway AND the free-molecule bounce clock, advanced by dt × the main
  speed slider `gSpeed`. The vdW boil (`uTb`, `gBoilT`) and the orbital electrons (`uTe`, `gElecT`) have their
  OWN clocks and dock sliders ('värinä', 'elektronit', 1.0× = the shaders' native rates), pushed into every
  ShaderMaterial through `gShaderMats` each frame (registered in `onNewMaterialAddedObservable` before the
  effect compiles, like `boilHzAdj`). Space pauses all three.
- Electron phase: the orb/bond vertex shaders hash it from the lobe's WORLD position, which re-seeds a moving
  molecule's electrons every frame (they looked ten times faster than protein electrons). The free orbital
  pools (`wOrbMat`, define SEEDATTR) carry a static per-slot `seed` thin-instance buffer instead.
- Lighting: key light with a depth darkening by distance past the orbit pivot (`gDepthK`,
  `gDepthLo`). Chlorophylls are green, carotenoids orange, by ETC cofactor type.
- Camera: ArcRotate. The wheel has an ABSOLUTE full step `gZoomMax` (63 units per notch) and a
  deterministic GEOMETRIC ramp: the first notch of a gesture is 10 percent of it, each notch multiplies
  by about 1.76 and the tenth lands on the ceiling of 16x the full step (2026-09-09, the owner wanted
  much faster acceleration with the first notch unchanged and the maximum at ten notches - 400 ms
  chain window, a pause resets). It pivots at what is under the cursor and bleeds inertially. Never make the step a
  fraction of a distance - the owner rejected that twice.
- Selection follows atoms on moving models (`followModelAtom`); you cannot select a protein
  you are inside. Dev switches: selections on/off, photons on/off.
- Dev mode panel: every tunable has a slider with a reset, and the current slider values are
  meant to be the shipped defaults (quality 2.01x, crisp 132, mega 600, blend 60, pan 0.21x,
  rotate 155 deg/s, vignette 1.00 / 40). Adaptive quality back-off was removed on request.

## Pitfalls already paid for

- NUCLEON instance matrices carry the atom centre in m[3], m[7], m[11] (world0.w, world1.w, world2.w),
  read by the imp vertex shader so a nucleus hashes its jitter and sway from the atom centre, not from
  each nucleon's own position (which scattered the cluster off centre). Never zero those slots, never
  let Babylon sync bounds from those meshes (`doNotSyncBoundingInfo`), and any new nucleon writer must
  pack them too (the lipid pool has a second writer that does not yet - those nucleons fall back).
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

## Start screen and the chemistry editor (mode 'editori')

index.html opens on a start screen (`#start`): 'Kemiaeditori' or 'Yhteyttamiskalvosto'. `?tila=editori` /
`?tila=kalvosto` skips it. The viewer is `run()`, called by `startViewer()` (which sets `html.kalvosto`).
The editor keeps the viewer's loading overlay (`#overlay`, exempt from the editori hide rule): `startEditor` sets the
label and shows 'Käynnistä keskeneräisenä' at once, `loadProgress()` in runEditor drives label and bar by the list
pictures done (thumbDone) out of TOTAL_ITEMS and lifts the screen at the last one (or after 90 s regardless).
`#back-btn` (Solukko's round 46 px button, top-left) exists in both modes, revealed by pointer movement and
faded 2.2 s after the pointer rests, and reloads without the query = the start screen. The editor list sits
below it (top 74) and the viewer's pill row is padded 74 px left. List items: a hovered long name glides
sideways (`.nimi-in.liuku`, `--dx` measured on mouseenter) and the picture is an IMG (a replaced element, 36 x 36, object-fit cover) - a span stretched with the row on some viewports. The editor is `runEditor()` in the
same script (shares the shaders and the globals ELEM / EL_LIST / codeOf / info / parseMol2). `html.editori` hides
every other body child, the editor's own DOM has class `.vesi` (the list `#lista`, a 'nopeus' slider).
- The list (`#lista-items`): the scene's 16 spawn elements, the small molecules (H2O, H+, CO2, O2, Pi, ATP, ADP,
  NADP+, chlorophyll, plastoquinone - ATP/ADP derived from nadph.mol2 exactly like the viewer's adpFromNadp, the
  rest from their mol2 files) and the 15 protein models (their mol2 files, loaded on first grab, cached).
- Dragging spawns the REAL molecule on pointerdown (`held`: no motion, no collisions) and it follows the pointer
  on the plane z = 0, released on pointerup with a velocity, taken back if dropped on the list.
  Right button held during a drag stamps copies of the held particle at the cursor every 0.5 s (the camera's
  right-drag look is suspended for the drag). The 'pyyhekumi' tool (`#eraser-btn`, next to the speed slider)
  removes the molecule under a left click and everything a left drag sweeps over (left-drag pan is off then).
- Arena 840 x 472 A (HW 420, HH 236) - RuBisCO (140 A) is a sixth of the width. Billiard bounce, masses = atom
  counts, RULES for the small species (H+H -> H2, O+O -> O2, H+O -> OH, OH+H -> H2O, H2+O -> H2O, H2+OH -> H2O+H,
  H2+O2 -> H2O+O, O2+H -> OH+O, OH+OH -> H2O+O), siblings of one reaction get 0.4 s grace against each other.
- Drawing: small molecules are rebuilt every frame into four dynamic thin-instance meshes (NOSWAY + SEEDATTR,
  fixed per-atom boil keys in the matrix w slots). A protein is binned into CELL = 60 cubes (the viewer's cell
  size) in local coordinates - per cell a crisp set (glass shell, nucleons, cores, bond lobes) and a CHEAP shell
  mesh (`protCheap`, the viewer's vdwLODfar recipe) - all moved by `gModelXform[slot]` (MODELMOVE, 80 slots).
  Per frame the viewer's rule: crisp when the cell's near edge is within REVEAL (132 = gCrisp) and in the
  frustum, else cheap thinned by projected atom size (protFrac), off when out of the frustum. Rendering group 1
  keeps depth (`setRenderingAutoClearDepthStencil(1,false)`) like the viewer - without it every shell painted
  over the lobes and hid them. Element colours only, no cofactor tints in the editor.
- Nucleons take no boil DRIFT (imp vertex shader, `#ifndef NUCLEON`): 0.02 units is invisible on a shell but
  a nucleon width on a nucleus and made every nucleus hop. Applies to the viewer's nucG too.
- Camera: ArcRotate, the viewer's FLIGHT - E/Q in and out along the view, A/D strafe, W/S screen-up/down
  (target and camera move together, so it passes through the plane), arrows turn, N/M roll, wheel zooms toward
  the cursor (detent ramp + smoothing), middle/right drag look, LEFT drag pans, merged gamepads, I resets, space
  pauses. No beta limits. Held keys ramp 5 % -> 100 % in 3.5 s.
- Selection: a left CLICK (< 4 px of motion) picks by a ray against every molecule's bounding sphere
  (`pickMol`, shared with the eraser): shells tint sage (proteins via the shader's selModel), `#valinta` card
  names it, the target eases onto it (`focusAnim`). Empty click or Esc clears.
- 2D / 3D toggle (`#mode3d-btn`): in 3D the arena is an 840 x 472 x 472 box (HD 236), particles get vz, bounce
  in z and tumble about their own axis (`ax3`) instead of the z-spin + rock. Back to 2D flattens z.
- List thumbnails = the info cards' pictures: atoms and molecules are rendered into `thumbRT` (128 px, transparent)
  with the card's recipe - lobes + nucleus only, no shell, alpha -pi/2.5, beta pi/2.7, fov 0.7, radius 3 x the
  orbital cloud (`sp.orbR`), a SQUARE projection frozen on the camera (else it takes the screen aspect and a wide screen squeezes every picture), one per frame from a queue that starts after 30 frames AND after the four
  dynamic materials are force-compiled (`thumbReady`). The molecule is spawned 50000 units out, the code waits one
  real frame (keyed on the frame counter - an observer added during onAfterRender can fire in the same pass) so the
  shared thin-instance buffers reach the GPU, then renders the target. A result under 1.5 % coverage is retried up to
  40 times, ten frames apart (`thumbWait`). Pitfall that cost a session: the render line is `... scene.activeCamera =
  thumbCam; thumbRT.render(); ...` with a trailing `//` comment - a comment inserted MID-line once swallowed the
  render call and every non-protein picture came out empty while all the buffer counts looked right. A protein gets the card's dot image
  (`drawProteinDots`, the viewer's drawProteinImage in a pastel of its own). File-based species join the queue
  when they load. A background preload (1.5 s after start, small files first, proteins smallest to largest)
  fetches and builds every file-based species so all pictures appear and a drop is instant. Species lobe
  arrays are typed (Float32Array) - every protein resident is ~1 GB heap.
- Electron spot: the orb/bond shaders (all variants) place each electron at the lobe's SURFACE POINT whose
  normal is the electron's direction (the ellipsoid support point, from the instance axes passed as vAx0-2 in
  view space, model/macro rotation included) and shade by WORLD distance - a spot of radius 0.06 with a 0.022
  core, the ripple in world units - so it is one round size on every lobe. It used to be a cap of normals, a
  fixed ANGLE: stretched along thin horns, huge on small cores. Lipid-baked lobes (LIPBAKE) carry no axes and
  keep the angular method. Thumbnails: a render under 1.5 % coverage is retried (a nucleus alone slipped past
  a blank check), a lobe-less species (the proton) renders with its shell instead.
  `window.gVesi` exposes spawn / remove / mols / SPECIES / ensureSpecies / cam for tests.

Moving molecules and the boil (both modes): the imp shader hashes the stepped boil offset and the silhouette
wobble phase from `hb`, exposed to the fragment as `vHb`. For a static atom that is its centre. A free molecule
in the viewer (WATERBOX) uses `wOrig`, the editor packs a fixed per-atom key into the matrix w slots - hashing the
LIVE centre re-rolled the offset every frame, a 60 Hz tremble against the lobes. Moving molecules get no thermal
sway at all (WATERBOX / NOSWAY in imp, SEEDATTR in orb and bond) - its phase is position-based and jittered at speed.

## Cell mode (tila=solu) - the whole plant cell (2026-09-09)

Third start-screen option 'Solu' (`?tila=solu`, `startViewer(true)` adds `html.solu`, `const SOLU` in run()). The
thylakoid scene is kept EXACTLY as it is and becomes the flat facet of the plasma membrane (a plant cell pressed
against its neighbour is flat there): every planar assumption in the file - MEMBRANE_Y, the particle box, the
protein footprints, the shuttles, the bouncers - is untouched. Around it, in `buildMembrane` under CELL MODE:
- Three closed membranes from the SAME lipid templates: the plasma membrane (CELL_R 8000, centre CEN straight
  above the sheet at cellYc = sqrt(R^2 - facetR^2), its bottom cap dropped onto the sheet's plane and skipped
  inside the sheet's rectangle), and the nuclear envelope (NE_R_OUT 2800, NE_R_IN 2500) with pores cut through
  both (NE_PORE_R 280, a jittered coarse lattice of NE_PORE_PITCH 0.5 rad, three cells in four carry one -
  `poreAt`, mirrored line for line in the `cellshell` shader with the same lowbias32 hash). Compressed scale on
  purpose (a 1.6 um cell): the owner chose it for the first step, real scale is two numbers away.
- Nothing is stored per lipid (a sphere this size carries ~40 M): an equi-angular CUBE lattice per sphere
  (FACE table, `dirOf`), blocks of BL x BL cells generated on demand by the sheet's own hashes (tileType /
  tileVar / tileJit with a per-face salt) and cached in a Map (`getBlock`, evicted after 600 frames unseen).
  Each frame `gatherCell` walks only the blocks in an angular window around the camera's foot on each face,
  with the sheet's three tiers: full lipids to memR, a strided prefix over the blend band, the shell past it.
  It runs INSIDE the sheet's gather (hook before the stream upload) into the same sphTpl / orbTpl streams
  (caps + CELL_EXTRA) and the same orbital candidate arrays (oRot / oTpl / oHasRot carry a frame).
- Every cell lipid is a ROTATED template (frame columns T, N, B - N the outward normal). The LIPTPL / LIPBAKE /
  LIPTILE shader paths now rotate the atom offset, memSway and ocen by mat3(W) (identity on the sheet), the
  nucleon pool gets a `tileRot` mat3 uniform (mesh.metadata.rot, `cellNearTiles` feeds it).
- Cell mode starts with the slab tier ON (`gSlabLod = SOLU`) and the sheet's own slab box stays off: the
  plasma membrane's shell carries the facet, rectangle included (footHalf 0 on that material). With the box
  on, the facet stood out of the cell - real lipids at every distance, and the box's side faces as a seam.
- The far tier is a `cellshell` mesh pair per membrane (outer and inner face, CreateSphere with the vertices
  rewritten via setVerticesData - updateVerticesData SILENTLY skips the GPU upload on a non-updatable buffer,
  which cost an hour), the slab shader's grain and hole plus a soft wrap by the angle to the camera.
- The background quad used to sit at NDC 0.99995, i.e. about 6000 units out with the 0.15 near plane: anything
  further was hidden behind it. It is at 0.9999995 now. `gWorldReach` includes the cell so the far clip
  reaches its far side, `upperRadiusLimit` 40000 in cell mode, three extra pills (solu, solukalvo,
  tumakotelo) fly there via `window.__cellGoto`. `window.__cell` exposes CEN, radii, the cache and `poreAt`.
- Not done yet: the closed membranes' lipids are not pickable (gPickLipid walks the sheet's lattice only), the
  pores are plain holes (the two membranes are not joined at the rim), the free molecules stay in the sheet's
  box (the cytosol between the box and the nucleus is empty), no cell wall, no chloroplasts, and the
  lattices of two cube faces (and the facet annulus against the sheet) meet with a visible seam up close.

### Organelles and the medium (2026-09-09, second step)

- The layout is pure data at the top of run(): `SOLU_CELL` (`CELL` was taken - it is the 60-unit cell size).
  Every membrane is an axis-aligned ellipsoid {C, R, s} in `SOLU_CELL.MEMS`: the plasma membrane, the nuclear
  envelope (pushed down toward the facet, as the vacuole does in a real plant cell), a vacuole, three chloroplasts
  (lens + inner envelope + four flat thylakoid discs), four mitochondria (outer + inner + three flat cristae), a
  Golgi stack of five cisternae, three ER sheets around the nucleus, six vesicles - 56 membranes. Positions were
  placed by hand with 150+ margins - move one and check its neighbours. `SOLU_CELL.ORG` (23) are the outer
  membranes that keep the free molecules out. `SOLU_CELL.surf(M, d)` is the one surface function (point +
  outward normal) shared by the lattice, the shells and the protein placement.
- An ellipsoid stretches the sphere lattice unevenly, so the pitch is set for the sparsest place (Jmax =
  det(S)/min(s)) and every cell is KEPT with probability J/Jmax (`Jat`, `keepH`): one even density, flat sacs
  included. Flat sacs get 8 x 8 blocks (their compressed rims would be thousands of near-empty 4 x 4 ones). The
  shell shader reads which face of the bilayer a fragment is on from a `surf` vertex attribute (+1 / -1) and the
  camera's side from `camSide`, so the band cut works on any shape - the old radial `hgt` is gone.
- The duplicate row (the '-row410' clones, DUP_ROWS stays 1) is placed in the organelles (`SOLU_CELL.PLACE`):
  b6f and ATP synthase in mitochondrion 1's inner membrane (stroma side = matrix), STN7 / PPH1 on a thylakoid
  disc, VDE / ZEP / FNR / Fd / PGR5 / PGRL1 floating between discs. Through gModelQuat / gModelOff /
  rebuildModelXform, so hull and shell follow. `gOrganelleModels` keeps them out of the bouncers AND out of the
  RTS floor flatten (which runs later and used to drag their z back to 0). No new heap: the facet keeps its
  first row only.
- The medium: in cell mode the free molecules' box REPEATS around the camera - `bnc` / `bncY` on the CPU wrap
  to the copy nearest the camera (bnc tells x from z by the bounds it is handed), the imp shader does the same
  under CELLCLIP - and a copy (never the base box, where the physics lives) is drawn only inside the cytosol:
  inside the plasma membrane, above the facet, outside every ORG ellipsoid by the bilayer's thickness measured
  along the local normal (`cytosol` in JS, the shader's twin). The six CPU sites that mirror positions (the
  water-orbital gather, the collision list, the proton lights, the picker, `near`, the free-orbital placer) call
  `gCellDrop`. The far haze (HAZE define, 120000 slow spheres of radius 5 in a box the size of the cell) is a
  sparse fill so the interior never looks empty from a distance - it may drift into the vacuole (hazeOk).
  Organelle interiors are empty of molecules for now.
- Measured in the preview pane: membranes 0.2 ms of the before-render CPU, the particle gathers 15 ms - the same
  as the plain thylakoid mode there (20 ms), so the owner's 4.5 ms machine should be fine.

### Picking, the look-around pivot, the far grain (2026-09-09, third step)

- The closed membranes' lipids are pickable: `gPickCell` (in the cell block, third hook in pickAtom's list after
  gPickFree / gPickLipid) walks the cached blocks inside the reveal bubble, rotates each atom's template offset
  and the sway by the lipid's frame exactly as LIPTPL draws it, and returns the same atom object as the
  sheet's picker (track = live centre, fill = the lobes rotated). `gSwayCPU` exports the sheet's sway mirror.
- `pickModelAtCursor` tests the ray in each model's BAKED frame (the inverse of gModelXform) against its baked
  box - the old box-plus-offset ignored the rotation, so tumbling bouncers, shuttles and the organelle-placed
  complexes missed the click.
- Cell mode look-around: a middle-drag pivots about a point LOOK_R = 20 units in front of the camera
  (`gLookPivot`, set at button-down, the pivot put back at the old distance along the new view once the drag
  and its inertia end). The shading plane reads `gFocalD()` (the old distance while re-pivoted) so the depth
  darkening does not jump during a turn. The thylakoid mode keeps its orbit. Arrow keys / the pad already
  looked around from the camera.
- The shell grain is MULTI-SCALE (`grain()` in the cellshell shader): the lipid-pitch cells up close, twice /
  four times / ... the pitch as they go sub-pixel, two levels blended - a large thing seen from far away is
  mottled, never a flat band (owner). The sheet's own slab shader still fades to its mean.
- Selections are ON by default in cell mode (`gSelEnabled = SOLU`) - on the sheet the dev switch 'valinnat' keeps
  them off, which is why 'nothing is selectable' there is not a bug.
- Organelle rainbow: `TINT` in the layout, by name prefix (nucleus violet, vacuole blue, chloroplast / thylakoid
  green, mitochondrion / crista red, Golgi pink, ER indigo, vesicle orange, the plasma membrane untinted). The
  near lipids get a per-instance `tint` thin-instance buffer (rgb + amount, the sheet's writer sets the amount
  to 0) that the LIPTPL path of the imp shader mixes into the vdW colour keeping the lipid's own light and dark -
  the orbital lobes keep their element colours - and the shells tint their slab colour the same way.
- The far clip reads `gFocalD()` and, in cell mode, is at least the distance to the cell's centre plus its
  radius: with the look pivot at 20 the old `ar*2 + reach` formula collapsed and the cell's sides vanished
  while turning. In cell mode I (resetView) and the start view are the whole cell from outside (CAM_DEF_TGT /
  CAM_DEF_POS rewritten in place), the same direction as the sheet's default.
- 'Käynnistä keskeneräisenä' shows a small bottom-centre bar (`#miniload`, driven by setBar / paintLbl, hidden
  when the bar completes). `#editortools` is laid out only under html.editori - its unconditional display:flex
  beat `.vesi{display:none}` and the editor's tool row sat in the viewer's dock.
