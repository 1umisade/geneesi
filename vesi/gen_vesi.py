import io, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root - this script lives in vesi/
NL = chr(10); CRLF = chr(13) + chr(10)
src = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8', newline='').read().replace(CRLF, NL)

def block(name):
    m = re.search(r"BABYLON\.Effect\.ShadersStore\['" + name + r"'\] = `.*?`;", src, re.S)
    assert m, name
    return m.group(0)
shaders = NL.join(block(n) for n in ['impVertexShader', 'impFragmentShader', 'bondVertexShader', 'bondFragmentShader', 'orbVertexShader', 'orbFragmentShader'])
bad = 0
for ln in shaders.split(NL):
    c = ln.find('//')
    if c >= 0 and ';' in ln[c:]: bad += 1; print('SEMICOLON IN COMMENT', ln.strip()[:80])
assert bad == 0

page = r'''<!DOCTYPE html>
<html lang="fi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vesimolekyyli</title>
<style>
:root{ --paper:#f2e6c9; --paper2:#e7d4ac; --brown:#4a3320; --ink:#3a2716; --sage:#a3b881; --sage2:#82a058; --sageink:#2f3d1c; }
html,body{margin:0;height:100%;overflow:hidden;background:var(--paper);font:13px/1.3 "Courier New",monospace;color:var(--ink)}
#c{position:fixed;inset:0;width:100%;height:100%;display:block;touch-action:none;outline:none}
.card{position:fixed;z-index:10;background:var(--paper);border:2.5px solid var(--brown);border-radius:14px;box-shadow:0 3px 0 var(--brown);padding:10px 12px;user-select:none}
#lista{left:16px;top:16px;display:flex;flex-direction:column;gap:10px;width:150px}
#lista h1{margin:0 0 2px;font-size:14px;letter-spacing:.5px}
#lista .ohje{font-size:11px;opacity:.75;line-height:1.35}
.atomi{display:flex;align-items:center;gap:10px;padding:7px 10px;border:2.5px solid var(--brown);border-radius:999px;background:var(--paper2);cursor:grab;touch-action:none}
.atomi:active{cursor:grabbing}
.atomi .pallo{width:22px;height:22px;border-radius:50%;border:2px solid var(--brown);box-sizing:border-box;flex:none}
.atomi b{font-size:13px}
.atomi small{display:block;font-size:10px;opacity:.7}
#laskuri{right:16px;top:16px;text-align:right}
#laskuri b{font-size:22px;margin-left:8px}
#laskuri .rivi{font-size:11px;opacity:.75;margin-top:4px}
#haamu{position:fixed;z-index:30;pointer-events:none;width:34px;height:34px;border-radius:50%;border:2.5px solid var(--brown);box-shadow:0 3px 0 var(--brown);transform:translate(-50%,-50%);display:none}
#vinkki{left:50%;bottom:16px;transform:translateX(-50%);font-size:12px;opacity:.85;white-space:nowrap}
</style>
</head>
<body>
<canvas id="c" tabindex="0"></canvas>
<div id="lista" class="card">
  <h1>Atomit</h1>
  <div class="ohje">Raahaa atomi näkymään. Ne pomppivat ja reagoivat törmätessään.</div>
  <div class="atomi" data-sp="H"><span class="pallo" style="background:#e0e0e0"></span><span><b>vety</b><small>H</small></span></div>
  <div class="atomi" data-sp="O"><span class="pallo" style="background:#f02626"></span><span><b>happi</b><small>O</small></span></div>
</div>
<div id="laskuri" class="card">vesimolekyylejä <b id="vesi-n">0</b><div class="rivi" id="muut"></div></div>
<div id="vinkki" class="card">2 H + O → H₂O &nbsp;·&nbsp; H + H → H₂ &nbsp;·&nbsp; O + O → O₂ &nbsp;·&nbsp; H₂ + O → H₂O</div>
<div id="haamu"></div>
<script src="https://cdn.babylonjs.com/babylon.js"></script>
<script>
/* ═══════════════════════════════════════════════════════════════════════════════════════════════
   Vesimolekyyli - a small companion page to the Geneesi thylakoid viewer (../index.html).
   Drag hydrogens and oxygens from the list into the view. They bounce on a plane perpendicular to the
   camera (billiard-ball reflection, the slower one yields), tumble a little so the 3-D shape reads, and
   react on contact: H+H → H2, O+O → O2, H+O → OH, OH+H → H2O, H2+O → H2O, and so on (RULES below).
   The atoms are drawn with the SAME shaders as Geneesi - the impostor vdW shell (glass, so the orbitals
   show through), the nucleon cluster, and the orbital lobes with their wandering electrons. The shader
   sources below are copied verbatim from ../index.html by vesi/gen_vesi.py - if they change
   there, regenerate. Rule for those sources: no semicolon in ANY GLSL comment (Babylon splits on it).
   ═══════════════════════════════════════════════════════════════════════════════════════════════ */
</script>
<script>
__SHADERS__
</script>
<script>
(() => {
'use strict';
/* ── element data (subset of Geneesi's ELEM table, same numbers) ─────────────────────────────── */
const FILL_SCALE = 0.72;
const ELEM = { H:{c:[0.88,0.88,0.88], vr:1.10, n:1,  z:1}, O:{c:[0.94,0.15,0.15], vr:1.52, n:16, z:8} };
const EL_LIST = ['H','O'], EL_CODE = { H:0, O:1 };
const info = code => ELEM[EL_LIST[code]];
const SHELL_STEP = 0.34;
const ECONF = { H:[[1,0]], O:[[1,0],[2,0],[2,1]] };
const econf = e => ECONF[EL_LIST[e]];
const OTMPL = [ [], [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]] ];   // s (sphere), p (6 lobes) - all that H and O need
const LP = { O:2 }; const lonePairs = e => LP[EL_LIST[e]] || 0;
const reachOf = sym => ECONF[sym].reduce((mx,sh) => Math.max(mx, sh[0]), 0) * SHELL_STEP;
const bondL = (a,b) => 0.52*(reachOf(a)+reachOf(b));   // Geneesi's stylised bond length
const NUCLEON_R = 0.013, SPACING = 1.55*NUCLEON_R, NUC_BIAS = 2.0;
const fcc = (() => { const p = []; for(let i=-4;i<=4;i++) for(let j=-4;j<=4;j++) for(let k=-4;k<=4;k++) if(((i+j+k)&1)===0) p.push([i,j,k, i*i+j*j+k*k]);
  p.sort((a,b) => a[3]-b[3]); const s = 1/Math.SQRT2; return p.map(q => [q[0]*s, q[1]*s, q[2]*s]); })();

/* ── lobe geometry helpers (copied from Geneesi) ───────────────────────────────────────────────── */
const _m = new BABYLON.Matrix(), _q = new BABYLON.Quaternion(), _s = new BABYLON.Vector3(), _p = new BABYLON.Vector3(), _ax = new BABYLON.Vector3();
const LOBE_W = 0.42;
function cylTo(sx,sy,sz, ex,ey,ez, dstBuf, dstOff, width){
  let dx=ex-sx, dy=ey-sy, dz=ez-sz;
  const len=Math.hypot(dx,dy,dz)||1e-6, inv=1/len; dx*=inv; dy*=inv; dz*=inv;
  if(dy>0.999999) _q.set(0,0,0,1);
  else if(dy<-0.999999) _q.set(1,0,0,0);
  else { _ax.set(dz,0,-dx); _ax.normalize(); BABYLON.Quaternion.RotationAxisToRef(_ax, Math.acos(dy), _q); }
  _s.set(width||LOBE_W,len,width||LOBE_W); _p.set((sx+ex)*0.5,(sy+ey)*0.5,(sz+ez)*0.5);
  BABYLON.Matrix.ComposeToRef(_s,_q,_p,_m); _m.copyToArray(dstBuf,dstOff);
}
const sphereMat = (cx,cy,cz, R, dstBuf, dstOff) => { _s.set(2*R,2*R,2*R); _q.set(0,0,0,1); _p.set(cx,cy,cz); BABYLON.Matrix.ComposeToRef(_s,_q,_p,_m); _m.copyToArray(dstBuf,dstOff); };
const H_LONG = 1.7, H_SHIFT = 0.55;   // a bonded hydrogen's 1s leans into the bond
const h1sMat = (cx,cy,cz, R, d, dst, off) => { const dx=d[0], dy=d[1], dz=d[2], S = 2*R;
  const ax = Math.abs(dy) < 0.9 ? [0,1,0] : [1,0,0];
  let ux=dy*ax[2]-dz*ax[1], uy=dz*ax[0]-dx*ax[2], uz=dx*ax[1]-dy*ax[0]; const ul=Math.hypot(ux,uy,uz)||1; ux/=ul; uy/=ul; uz/=ul;
  const wx=dy*uz-dz*uy, wy=dz*ux-dx*uz, wz=dx*uy-dy*ux;
  dst[off]=ux*S; dst[off+1]=uy*S; dst[off+2]=uz*S; dst[off+3]=0;
  dst[off+4]=wx*S; dst[off+5]=wy*S; dst[off+6]=wz*S; dst[off+7]=0;
  dst[off+8]=dx*S*H_LONG; dst[off+9]=dy*S*H_LONG; dst[off+10]=dz*S*H_LONG; dst[off+11]=0;
  dst[off+12]=cx+dx*S*H_SHIFT; dst[off+13]=cy+dy*S*H_SHIFT; dst[off+14]=cz+dz*S*H_SHIFT; dst[off+15]=1; };
const nrm = v => { const l=Math.hypot(v[0],v[1],v[2])||1e-6; return [v[0]/l,v[1]/l,v[2]/l]; };
const crs = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const perp = v => { const a = Math.abs(v[0])<0.9 ? [1,0,0] : [0,1,0]; return nrm(crs(v,a)); };
const rotAx = (v,k,ang) => { const c=Math.cos(ang), s=Math.sin(ang), kv=crs(k,v), d=k[0]*v[0]+k[1]*v[1]+k[2]*v[2];
  return [v[0]*c+kv[0]*s+k[0]*d*(1-c), v[1]*c+kv[1]*s+k[1]*d*(1-c), v[2]*c+kv[2]*s+k[2]*d*(1-c)]; };
function lonePairDirs(dirs, lp){
  if(dirs.length===0) return [];
  const bis = nrm([-(dirs.reduce((s,d)=>s+d[0],0)), -(dirs.reduce((s,d)=>s+d[1],0)), -(dirs.reduce((s,d)=>s+d[2],0))]);
  if(lp===1) return [bis];
  const axis = dirs.length>=2 ? nrm(crs(dirs[0],dirs[1])) : perp(dirs[0]);
  return [rotAx(bis,axis,0.9553), rotAx(bis,axis,-0.9553)];
}
/* rigidOrbSet - Geneesi's orbital builder for a small rigid molecule: cores (s spheres, p lobes), sigma
   horns and back knobs per bond, a pi cloud on double bonds, lone pairs by VSEPR. m = {na,x,y,z,el,nb,b1,b2,bo}. */
const rigidOrbSet = m => {
  const core = { m:[], col:[], cen:[], oid:[] }, bond = { m:[], tap:[], col:[], cen:[], oid:[], prof:[] };
  const tmp = new Float32Array(16), N = m.na, at = [], els = [];
  let cx=0, cy=0, cz=0; for(let k=0;k<N;k++){ cx+=m.x[k]; cy+=m.y[k]; cz+=m.z[k]; } cx/=N; cy/=N; cz/=N;
  for(let k=0;k<N;k++){ at.push([m.x[k]-cx, m.y[k]-cy, m.z[k]-cz]); els.push(m.el[k]); }
  const pushCore = (c,x,y,z,oid) => { for(let j=0;j<16;j++) core.m.push(tmp[j]); core.col.push(c[0],c[1],c[2]); core.cen.push(x,y,z); core.oid.push(oid); };
  const put = (sx,sy,sz, ex,ey,ez, wid, c, x,y,z, oid, tap, prof) => { cylTo(sx,sy,sz, ex,ey,ez, tmp, 0, wid);
    for(let j=0;j<16;j++) bond.m.push(tmp[j]);
    bond.tap.push(tap === undefined ? 1.0 : tap); bond.col.push(c[0],c[1],c[2]); bond.cen.push(x,y,z); bond.oid.push(oid); bond.prof.push(prof ? 1.0 : 0.0); };
  const bd = at.map(() => []);
  for(let b=0;b<m.nb;b++){ const i=m.b1[b], j=m.b2[b];
    const d = nrm([at[j][0]-at[i][0], at[j][1]-at[i][1], at[j][2]-at[i][2]]); bd[i].push(d); bd[j].push([-d[0],-d[1],-d[2]]); }
  for(let k=0;k<N;k++){ const e=els[k], cfg=econf(e), maxNe=cfg.reduce((mx,sh)=>Math.max(mx,sh[0]),0), q=at[k], c=info(e).c, bonded=bd[k].length>0;
    for(const sh of cfg){ const n2=sh[0], ty=sh[1], R=n2*SHELL_STEP, oid=n2*100+ty*10;
      if(bonded && maxNe>1 && n2===maxNe && ty<=1) continue;
      if(ty===0){ if(bonded && EL_LIST[e]==='H') h1sMat(q[0],q[1],q[2], R*0.72, bd[k][0], tmp, 0); else sphereMat(q[0],q[1],q[2], R*0.72, tmp, 0); pushCore(c,q[0],q[1],q[2],oid); }
      else for(const d of OTMPL[ty]){ cylTo(q[0],q[1],q[2], q[0]+d[0]*R,q[1]+d[1]*R,q[2]+d[2]*R, tmp,0,R*0.34); pushCore(c,q[0],q[1],q[2],oid); } } }
  const pn = bd.map(dirs => { for(let a=0;a<dirs.length;a++) for(let b=a+1;b<dirs.length;b++){ const cr=crs(dirs[a],dirs[b]), l=Math.hypot(cr[0],cr[1],cr[2]); if(l>0.3) return [cr[0]/l,cr[1]/l,cr[2]/l]; } return null; });
  const f=0.62, kL=0.24, kW=LOBE_W*0.5, pw=LOBE_W*0.42, pR=0.62; let hyb=0;
  for(let b=0;b<m.nb;b++){ const i=m.b1[b], j=m.b2[b], bo=m.bo ? m.bo[b] : 1;
    const p1=at[i], p2=at[j], bx=p2[0]-p1[0], by=p2[1]-p1[1], bz=p2[2]-p1[2], BL=Math.hypot(bx,by,bz)||1e-6, u=[bx/BL,by/BL,bz/BL];
    const c1=info(els[i]).c, c2=info(els[j]).c, h1=EL_LIST[els[i]]==='H', h2=EL_LIST[els[j]]==='H';
    const sw = bo >= 2 ? LOBE_W*1.35 : LOBE_W, sprof = bo >= 2;
    if(!h1) put(p1[0],p1[1],p1[2], p1[0]+bx*f,p1[1]+by*f,p1[2]+bz*f, sw, c1, p1[0],p1[1],p1[2], 1000+(hyb++), 1.0, sprof);
    if(!h2) put(p2[0],p2[1],p2[2], p2[0]-bx*f,p2[1]-by*f,p2[2]-bz*f, sw, c2, p2[0],p2[1],p2[2], 1000+(hyb++), 1.0, sprof);
    if(!h1) put(p1[0],p1[1],p1[2], p1[0]-u[0]*kL,p1[1]-u[1]*kL,p1[2]-u[2]*kL, kW, c1, p1[0],p1[1],p1[2], 1000);
    if(!h2) put(p2[0],p2[1],p2[2], p2[0]+u[0]*kL,p2[1]+u[1]*kL,p2[2]+u[2]*kL, kW, c2, p2[0],p2[1],p2[2], 1000);
    if(bo >= 2){ const nv = pn[i] || pn[j] || nrm(crs([bx,by,bz], Math.abs(bx)<0.9*BL ? [1,0,0] : [0,1,0]));
      const mx=(p1[0]+p2[0])/2, my=(p1[1]+p2[1])/2, mz=(p1[2]+p2[2])/2, cm=[(c1[0]+c2[0])*0.5,(c1[1]+c2[1])*0.5,(c1[2]+c2[2])*0.5];
      for(const sg of [1,-1]){ const ex=nv[0]*pR*sg, ey=nv[1]*pR*sg, ez=nv[2]*pR*sg;
        put(p1[0]+ex,p1[1]+ey,p1[2]+ez, p2[0]+ex,p2[1]+ey,p2[2]+ez, pw*1.7, cm, mx,my,mz, 1002, 0.9); } } }
  for(let k=0;k<N;k++){ const q=at[k], c=info(els[k]).c, lpn=lonePairs(els[k]);
    if(lpn===0 || bd[k].length===0) continue;
    for(const d of lonePairDirs(bd[k], lpn)) put(q[0],q[1],q[2], q[0]+d[0]*0.75,q[1]+d[1]*0.75,q[2]+d[2]*0.75, LOBE_W, c, q[0],q[1],q[2], 2000); }
  return { core, bond, at, els };
};

/* ── species: local geometry (centroid at the origin, in the z=0 plane) + their drawn parts ────── */
const mkModel = (atoms, bonds) => { const na = atoms.length; const m = { na, x:new Float32Array(na), y:new Float32Array(na), z:new Float32Array(na), el:new Uint16Array(na), nb:bonds.length, b1:new Int32Array(bonds.length), b2:new Int32Array(bonds.length), bo:new Uint8Array(bonds.length) };
  atoms.forEach((a,k) => { m.x[k]=a[1]; m.y[k]=a[2]; m.z[k]=a[3]||0; m.el[k]=EL_CODE[a[0]]; }); bonds.forEach((b,k) => { m.b1[k]=b[0]; m.b2[k]=b[1]; m.bo[k]=b[2]||1; }); return m; };
const dHH = bondL('H','H'), dOO = bondL('O','O'), dOH = bondL('O','H'), ang = 104.5*Math.PI/180;
const MODELS = {
  H:   mkModel([['H',0,0]], []),
  O:   mkModel([['O',0,0]], []),
  H2:  mkModel([['H',-dHH/2,0],['H',dHH/2,0]], [[0,1,1]]),
  O2:  mkModel([['O',-dOO/2,0],['O',dOO/2,0]], [[0,1,2]]),
  OH:  mkModel([['O',0,0],['H',dOH,0]], [[0,1,1]]),
  H2O: mkModel([['O',0,0],['H',dOH*Math.cos(ang/2),dOH*Math.sin(ang/2)],['H',dOH*Math.cos(ang/2),-dOH*Math.sin(ang/2)]], [[0,1,1],[0,2,1]]),
};
const NAME_FI = { H:'vety', O:'happi', H2:'vetymolekyyli H₂', O2:'happimolekyyli O₂', OH:'hydroksyyli OH', H2O:'vesi H₂O' };
const PC = [1.0, 0.5, 0.5], NC = [0.62, 0.62, 0.62];   // protons light red, neutrons grey (Geneesi)
const SPECIES = {};
for(const key in MODELS){ const m = MODELS[key], orb = rigidOrbSet(m);
  const atoms = orb.at.map((q,k) => { const e = orb.els[k], I = info(e); const A = I.n, Z = I.z, nuc = [];
    for(let i=0;i<A;i++){ const proton = Math.floor((i+1)*Z/A) > Math.floor(i*Z/A); nuc.push({ o:[fcc[i][0]*SPACING, fcc[i][1]*SPACING, fcc[i][2]*SPACING], col: proton ? PC : NC, p: proton ? 1 : 0 }); }
    return { q, r: I.vr*FILL_SCALE, col: I.c, nuc }; });
  const radius = atoms.reduce((mx,a) => Math.max(mx, Math.hypot(a.q[0],a.q[1],a.q[2]) + a.r), 0);
  SPECIES[key] = { key, model: m, core: orb.core, bond: orb.bond, atoms, radius, mass: m.na, coreN: orb.core.m.length/16, bondN: orb.bond.m.length/16 }; }

/* ── reactions: an unordered pair of species → the products that leave the collision ─────────── */
const RULES = {};
const rule = (a, b, prods) => { RULES[a+'+'+b] = prods; RULES[b+'+'+a] = prods; };
rule('H','H',['H2']); rule('O','O',['O2']); rule('H','O',['OH']);
rule('OH','H',['H2O']); rule('H2','O',['H2O']); rule('H2','OH',['H2O','H']); rule('H2','O2',['H2O','O']);
rule('O2','H',['OH','O']); rule('OH','OH',['H2O','O']);

/* ── Babylon scene ─────────────────────────────────────────────────────────────────────────────── */
const canvas = document.getElementById('c');
const engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer: false, stencil: false, antialias: true });
const scene = new BABYLON.Scene(engine);
const PAPER = new BABYLON.Color3(0.949, 0.902, 0.788);
scene.clearColor = new BABYLON.Color4(PAPER.r, PAPER.g, PAPER.b, 1);
scene.fogColor = PAPER; scene.fogStart = 1e8; scene.fogEnd = 1e9;   // the shaders fog by distance - pushed out of reach
scene.skipPointerMovePicking = true; scene.autoClear = true;
/* the camera looks straight down +Z at the plane z = 0 - the particles never leave that plane */
const HALF_H = 9;    // half the visible height at the plane (world units = Å)
const cam = new BABYLON.FreeCamera('cam', new BABYLON.Vector3(0, 0, -HALF_H / Math.tan(0.4)), scene);
cam.fov = 0.8; cam.setTarget(BABYLON.Vector3.Zero()); cam.minZ = 0.5; cam.maxZ = 500;
const halfW = () => HALF_H * engine.getRenderWidth() / engine.getRenderHeight();

/* ── clocks: sway (uT), boil (uTb), electrons (uTe) - the same three Geneesi drives ─────────────── */
let uT = 0, uTb = 0, uTe = 0; const BOIL = 0.20, ELEC_RATE = 1.0, BOIL_RATE = 1.0;

/* ── materials: the exact Geneesi recipes for a free-standing atom ──────────────────────────────── */
const realAlpha = mat => { mat.alpha = 0.999; mat.alphaMode = BABYLON.Constants.ALPHA_COMBINE; mat.forceDepthWrite = true; return mat; };
const FAR = new BABYLON.Vector3(1e6, 1e6, 1e6);
const shellMat = new BABYLON.ShaderMaterial('shell', scene, 'imp', {
  attributes:['position','instanceColor','world0','world1','world2','world3','instR'],
  uniforms:['view','projection','radius','fogColor','fogStart','fogEnd','isShell','shellMin','revealFade','bubbleR','protonOutline','uT','uTb','boil','boilHzAdj','depthBias','selCenter','coneCos','selModel','selCol'],
  defines:['#define IMPRAD'] });
shellMat.setFloat('radius',1.0); shellMat.setFloat('isShell',1); shellMat.setFloat('shellMin',0.22); shellMat.setFloat('revealFade',0.95);
shellMat.setFloat('bubbleR',1e9); shellMat.setFloat('protonOutline',0); shellMat.setFloat('depthBias',0); shellMat.setFloat('boil',BOIL); shellMat.setFloat('boilHzAdj',0);
shellMat.setFloat('coneCos',-1.0); shellMat.setVector3('selCenter', FAR); shellMat.setFloat('selModel',-1); shellMat.setColor3('selCol', new BABYLON.Color3(0.64,0.72,0.51)); shellMat.backFaceCulling=false; realAlpha(shellMat);
const nucMat = new BABYLON.ShaderMaterial('nuc', scene, 'imp', {
  attributes:['position','instanceColor','world0','world1','world2','world3'],
  uniforms:['view','projection','radius','fogColor','fogStart','fogEnd','isShell','shellMin','revealFade','bubbleR','protonOutline','uT','uTb','boil','boilHzAdj','depthBias','selCenter','coneCos','selModel','selCol'] });
nucMat.setFloat('radius',NUCLEON_R); nucMat.setFloat('isShell',0); nucMat.setFloat('shellMin',0); nucMat.setFloat('revealFade',0); nucMat.setFloat('bubbleR',1e9); nucMat.setFloat('protonOutline',0);
nucMat.setFloat('depthBias',NUC_BIAS); nucMat.setFloat('boil',BOIL); nucMat.setFloat('boilHzAdj',0); nucMat.setFloat('coneCos',-1.0); nucMat.setVector3('selCenter', FAR); nucMat.setFloat('selModel',-1); nucMat.setColor3('selCol', new BABYLON.Color3(0.64,0.72,0.51));
nucMat.backFaceCulling=false; realAlpha(nucMat); nucMat.disableDepthWrite = true;
const orbMatOf = (nm, shader, attrs, extra, defs) => { const m = new BABYLON.ShaderMaterial(nm, scene, shader, { attributes: attrs.concat(['seed']),
    uniforms:['view','projection','bubbleR','fogColor','fogStart','fogEnd','uT','uTe','nElec','selCenter','focusId','coneCos','drawElec','selModel','selCol','focusAmt','focusMode','focusCenterV','focusR','focusDark'].concat(extra||[]),
    defines:['#define SEEDATTR'].concat(defs||[]) });
  m.setFloat('bubbleR',1e9); m.setFloat('nElec',2); m.setFloat('coneCos',-1.0); m.setFloat('drawElec',1); m.setVector3('selCenter', FAR); m.setFloat('focusId',-1);
  m.setFloat('selModel',-1); m.setColor3('selCol', new BABYLON.Color3(0.64,0.72,0.51)); m.setFloat('focusAmt',0); m.setFloat('focusMode',0); m.setVector3('focusCenterV', FAR); m.setFloat('focusR',0); m.setFloat('focusDark',0);
  m.backFaceCulling = true; return realAlpha(m); };
const coreMat = orbMatOf('orbCore','orb',['position','normal','ocol','ocen','oid','world0','world1','world2','world3']);
const bondMat = orbMatOf('orbBond','bond',['position','normal','taper','prof','ocen','bcol','oid','world0','world1','world2','world3'],['opacity'],['#define HORNPROF']);
bondMat.setFloat('nElec',1); bondMat.setFloat('opacity',1);
for(const m of [shellMat, nucMat, coreMat, bondMat]) m.onBindObservable.add(() => { const e = m.getEffect(); if(!e) return;
  e.setFloat('uT', uT); e.setFloat('uTb', uTb); e.setFloat('uTe', uTe); e.setColor3('fogColor', scene.fogColor); e.setFloat('fogStart', scene.fogStart); e.setFloat('fogEnd', scene.fogEnd); });

/* ── the four instanced meshes (orbitals in group 0, shells and nuclei over them in group 1) ───── */
const MAXMOL = 80, MAXATOM = MAXMOL*3, MAXNUC = MAXMOL*3*16, MAXLOBE = MAXMOL*40;
const mkMesh = (nm, mesh, mat, grp) => { mesh.material = mat; mesh.isPickable = false; mesh.alwaysSelectAsActiveMesh = true; mesh.renderingGroupId = grp; mesh.doNotSyncBoundingInfo = true; return mesh; };
const shellMesh = mkMesh('shells', BABYLON.MeshBuilder.CreatePlane('shells', {size:2}, scene), shellMat, 1);
const nucMesh   = mkMesh('nuclei', BABYLON.MeshBuilder.CreatePlane('nuclei', {size:2}, scene), nucMat, 1);
const coreMesh  = mkMesh('cores',  BABYLON.MeshBuilder.CreateSphere('cores', {segments:6, diameter:1}, scene), coreMat, 0);
const bondMesh  = mkMesh('lobes',  BABYLON.MeshBuilder.CreateSphere('lobes', {segments:5, diameter:1}, scene), bondMat, 0);
const B = {
  shM: new Float32Array(MAXATOM*16), shC: new Float32Array(MAXATOM*4), shR: new Float32Array(MAXATOM),
  nuM: new Float32Array(MAXNUC*16),  nuC: new Float32Array(MAXNUC*4),
  coM: new Float32Array(MAXLOBE*16), coCol: new Float32Array(MAXLOBE*3), coCen: new Float32Array(MAXLOBE*3), coOid: new Float32Array(MAXLOBE), coSeed: new Float32Array(MAXLOBE),
  boM: new Float32Array(MAXLOBE*16), boCol: new Float32Array(MAXLOBE*3), boCen: new Float32Array(MAXLOBE*3), boOid: new Float32Array(MAXLOBE), boSeed: new Float32Array(MAXLOBE), boTap: new Float32Array(MAXLOBE), boProf: new Float32Array(MAXLOBE) };
shellMesh.thinInstanceSetBuffer('matrix', B.shM, 16, false); shellMesh.thinInstanceSetBuffer('instanceColor', B.shC, 4, false); shellMesh.thinInstanceSetBuffer('instR', B.shR, 1, false);
nucMesh.thinInstanceSetBuffer('matrix', B.nuM, 16, false); nucMesh.thinInstanceSetBuffer('instanceColor', B.nuC, 4, false);
coreMesh.thinInstanceSetBuffer('matrix', B.coM, 16, false); coreMesh.thinInstanceSetBuffer('ocol', B.coCol, 3, false); coreMesh.thinInstanceSetBuffer('ocen', B.coCen, 3, false); coreMesh.thinInstanceSetBuffer('oid', B.coOid, 1, false); coreMesh.thinInstanceSetBuffer('seed', B.coSeed, 1, false);
bondMesh.thinInstanceSetBuffer('matrix', B.boM, 16, false); bondMesh.thinInstanceSetBuffer('bcol', B.boCol, 3, false); bondMesh.thinInstanceSetBuffer('ocen', B.boCen, 3, false); bondMesh.thinInstanceSetBuffer('oid', B.boOid, 1, false); bondMesh.thinInstanceSetBuffer('seed', B.boSeed, 1, false); bondMesh.thinInstanceSetBuffer('taper', B.boTap, 1, false); bondMesh.thinInstanceSetBuffer('prof', B.boProf, 1, false);
for(const m of [shellMesh, nucMesh, coreMesh, bondMesh]) m.thinInstanceCount = 0;

/* ── the molecules ─────────────────────────────────────────────────────────────────────────────── */
const mols = []; let nextId = 1, rxId = 0;
const rnd = (a, b) => a + Math.random()*(b - a);
const spawn = (key, x, y, vx, vy, grp) => { const sp = SPECIES[key]; if(!sp || mols.length >= MAXMOL) return null;
  if(vx === undefined){ const a = Math.random()*6.283, s = rnd(2.5, 4.5); vx = Math.cos(a)*s; vy = Math.sin(a)*s; }
  const m = { id: nextId++, sp, x, y, vx, vy, ang: Math.random()*6.283, angV: rnd(0.25, 0.6) * (Math.random() < 0.5 ? -1 : 1),
    rockAx: Math.random()*6.283, rockPh: Math.random()*6.283, rockAmp: rnd(0.35, 0.55), born: uT, grp: grp || 0 };   // grp = the reaction that made it (0 = dropped by hand): siblings get a moment before they may react with EACH OTHER again
  mols.push(m); fmt(); return m; };
const hash = (a, b) => { const v = Math.sin(a*12.9898 + b*78.233) * 43758.5453; return v - Math.floor(v); };
const fmt = () => { let nw = 0; const cnt = {}; for(const m of mols){ if(m.sp.key === 'H2O') nw++; cnt[m.sp.key] = (cnt[m.sp.key]||0) + 1; }
  document.getElementById('vesi-n').textContent = nw;
  document.getElementById('muut').textContent = Object.keys(cnt).filter(k => k !== 'H2O').sort().map(k => NAME_FI[k].split(' ')[0] + ' ' + cnt[k]).join(' · '); };

/* ── physics: billiard bounce on the plane, then the reaction table ────────────────────────────── */
const step = dt => {
  const W = halfW(), H = HALF_H;
  for(const m of mols){ m.x += m.vx*dt; m.y += m.vy*dt; m.ang += m.angV*dt; const r = m.sp.radius;
    if(m.x < -W + r){ m.x = -W + r; m.vx = Math.abs(m.vx); m.angV = -m.angV; } else if(m.x > W - r){ m.x = W - r; m.vx = -Math.abs(m.vx); m.angV = -m.angV; }
    if(m.y < -H + r){ m.y = -H + r; m.vy = Math.abs(m.vy); m.angV = -m.angV; } else if(m.y > H - r){ m.y = H - r; m.vy = -Math.abs(m.vy); m.angV = -m.angV; } }
  const dead = new Set(), born = [];
  for(let i=0;i<mols.length;i++){ const a = mols[i]; if(dead.has(a)) continue;
    for(let j=i+1;j<mols.length;j++){ const b = mols[j]; if(dead.has(b)) continue;
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy), R = a.sp.radius + b.sp.radius; if(d >= R || d < 1e-6) continue;
      const nx = dx/d, ny = dy/d;
      const siblings = a.grp && a.grp === b.grp && uT - a.born < 0.4;   // products of the SAME reaction, still flying apart - not again with each other yet
      const prods = siblings ? null : RULES[a.sp.key + '+' + b.sp.key];
      if(prods){ dead.add(a); dead.add(b); const g = ++rxId;
        const M = a.sp.mass + b.sp.mass, vx = (a.vx*a.sp.mass + b.vx*b.sp.mass)/M, vy = (a.vy*a.sp.mass + b.vy*b.sp.mass)/M, cx = (a.x + b.x)/2, cy = (a.y + b.y)/2;
        prods.forEach((k, q) => { const sp = SPECIES[k]; if(q === 0) born.push([k, cx, cy, vx, vy, g]);
          else { const s = Math.hypot(vx, vy) + 1.5, px = -ny, py = nx, side = q % 2 ? 1 : -1; born.push([k, cx + px*side*(sp.radius + SPECIES[prods[0]].radius + 0.2), cy + py*side*(sp.radius + SPECIES[prods[0]].radius + 0.2), px*side*s, py*side*s, g]); } });
        break; }   // a is consumed - it must not react with the next partner in the same frame (two H on one O gave two OH)
      // elastic bounce (masses = atom counts), then push apart
      const ma = a.sp.mass, mb = b.sp.mass, rv = (b.vx - a.vx)*nx + (b.vy - a.vy)*ny; if(rv < 0){ const jn = -2*rv/(1/ma + 1/mb); a.vx -= jn*nx/ma; a.vy -= jn*ny/ma; b.vx += jn*nx/mb; b.vy += jn*ny/mb; a.angV = -a.angV; b.angV = -b.angV; }
      const ov = (R - d)*0.5 + 0.01; a.x -= nx*ov; a.y -= ny*ov; b.x += nx*ov; b.y += ny*ov; } }
  if(dead.size){ for(let i=mols.length-1;i>=0;i--) if(dead.has(mols[i])) mols.splice(i, 1); for(const b of born) spawn(...b); fmt(); }
};

/* ── drawing: every frame, every molecule's parts go into the four instance buffers ────────────── */
const R9 = new Float64Array(9), T16 = new Float32Array(16);
const rotOf = (m, t) => { // z-spin composed with a gentle rock about an in-plane axis, so the 3-D shape reads
  const cz = Math.cos(m.ang), sz = Math.sin(m.ang), th = m.rockAmp*Math.sin(t*0.8 + m.rockPh), c = Math.cos(th), s = Math.sin(th), k = [Math.cos(m.rockAx), Math.sin(m.rockAx), 0], tt = 1 - c;
  const Rk = [tt*k[0]*k[0]+c, tt*k[0]*k[1], s*k[1],  tt*k[0]*k[1], tt*k[1]*k[1]+c, -s*k[0],  -s*k[1], s*k[0], c];   // rotation about k (row-major)
  const Rz = [cz,-sz,0, sz,cz,0, 0,0,1];
  for(let r=0;r<3;r++) for(let cc=0;cc<3;cc++) R9[r*3+cc] = Rk[r*3]*Rz[cc] + Rk[r*3+1]*Rz[3+cc] + Rk[r*3+2]*Rz[6+cc]; };
const xf = (v, out) => { out[0] = R9[0]*v[0] + R9[1]*v[1] + R9[2]*v[2]; out[1] = R9[3]*v[0] + R9[4]*v[1] + R9[5]*v[2]; out[2] = R9[6]*v[0] + R9[7]*v[1] + R9[8]*v[2]; return out; };
const _v = [0,0,0], _w = [0,0,0];
const draw = () => {
  let na = 0, nn = 0, nc = 0, nb = 0;
  for(const m of mols){ rotOf(m, uT); const sp = m.sp, px = m.x, py = m.y;
    for(const a of sp.atoms){ xf(a.q, _v); const ax = px + _v[0], ay = py + _v[1], az = _v[2];
      let o = na*16; B.shM.fill(0, o, o+16); B.shM[o]=1; B.shM[o+5]=1; B.shM[o+10]=1; B.shM[o+15]=1; B.shM[o+12]=ax; B.shM[o+13]=ay; B.shM[o+14]=az;
      B.shC[na*4]=a.col[0]; B.shC[na*4+1]=a.col[1]; B.shC[na*4+2]=a.col[2]; B.shC[na*4+3]=0; B.shR[na]=a.r; na++;
      for(const n of a.nuc){ xf(n.o, _w); o = nn*16; B.nuM.fill(0, o, o+16); B.nuM[o]=1; B.nuM[o+5]=1; B.nuM[o+10]=1; B.nuM[o+15]=1;
        B.nuM[o+12]=ax+_w[0]; B.nuM[o+13]=ay+_w[1]; B.nuM[o+14]=az+_w[2]; B.nuM[o+3]=ax; B.nuM[o+7]=ay; B.nuM[o+11]=az;   // the atom centre rides in the w slots (see the imp vertex shader)
        B.nuC[nn*4]=n.col[0]; B.nuC[nn*4+1]=n.col[1]; B.nuC[nn*4+2]=n.col[2]; B.nuC[nn*4+3]=n.p; nn++; } }
    const putLobe = (src, q, M, COL, CEN, OID, SEED, idx, extra) => { const s0 = q*16, d0 = idx*16;
      for(let c=0;c<3;c++){ const ax=src.m[s0+c*4], ay=src.m[s0+c*4+1], az=src.m[s0+c*4+2];
        M[d0+c*4]  =R9[0]*ax+R9[1]*ay+R9[2]*az; M[d0+c*4+1]=R9[3]*ax+R9[4]*ay+R9[5]*az; M[d0+c*4+2]=R9[6]*ax+R9[7]*ay+R9[8]*az; M[d0+c*4+3]=0; }
      const mx=src.m[s0+12], my=src.m[s0+13], mz=src.m[s0+14];
      M[d0+12]=R9[0]*mx+R9[1]*my+R9[2]*mz+px; M[d0+13]=R9[3]*mx+R9[4]*my+R9[5]*mz+py; M[d0+14]=R9[6]*mx+R9[7]*my+R9[8]*mz; M[d0+15]=1;
      const ex=src.cen[q*3], ey=src.cen[q*3+1], ez=src.cen[q*3+2];
      CEN[idx*3]=R9[0]*ex+R9[1]*ey+R9[2]*ez+px; CEN[idx*3+1]=R9[3]*ex+R9[4]*ey+R9[5]*ez+py; CEN[idx*3+2]=R9[6]*ex+R9[7]*ey+R9[8]*ez;
      COL[idx*3]=src.col[q*3]; COL[idx*3+1]=src.col[q*3+1]; COL[idx*3+2]=src.col[q*3+2]; OID[idx]=src.oid[q]; SEED[idx]=hash(m.id, q); if(extra) extra(idx, q); };
    for(let q=0;q<sp.coreN && nc<MAXLOBE;q++, nc++) putLobe(sp.core, q, B.coM, B.coCol, B.coCen, B.coOid, B.coSeed, nc);
    for(let q=0;q<sp.bondN && nb<MAXLOBE;q++, nb++) putLobe(sp.bond, q, B.boM, B.boCol, B.boCen, B.boOid, B.boSeed, nb, (i, k) => { B.boTap[i] = sp.bond.tap[k]; B.boProf[i] = sp.bond.prof[k]; }); }
  shellMesh.thinInstanceCount = na; nucMesh.thinInstanceCount = nn; coreMesh.thinInstanceCount = nc; bondMesh.thinInstanceCount = nb;
  if(na){ shellMesh.thinInstanceBufferUpdated('matrix'); shellMesh.thinInstanceBufferUpdated('instanceColor'); shellMesh.thinInstanceBufferUpdated('instR'); }
  if(nn){ nucMesh.thinInstanceBufferUpdated('matrix'); nucMesh.thinInstanceBufferUpdated('instanceColor'); }
  if(nc){ for(const k of ['matrix','ocol','ocen','oid','seed']) coreMesh.thinInstanceBufferUpdated(k); }
  if(nb){ for(const k of ['matrix','bcol','ocen','oid','seed','taper','prof']) bondMesh.thinInstanceBufferUpdated(k); }
  shellMesh.setEnabled(na > 0); nucMesh.setEnabled(nn > 0); coreMesh.setEnabled(nc > 0); bondMesh.setEnabled(nb > 0);
};

scene.onBeforeRenderObservable.add(() => { const dt = Math.min(engine.getDeltaTime(), 50) * 0.001; uT += dt; uTb += dt*BOIL_RATE; uTe += dt*ELEC_RATE; step(dt); draw(); });
engine.runRenderLoop(() => scene.render());
window.addEventListener('resize', () => engine.resize());

/* ── drag from the list onto the plane ─────────────────────────────────────────────────────────── */
const ghost = document.getElementById('haamu');
const toPlane = (cx, cy) => { const ray = scene.createPickingRay(cx, cy, BABYLON.Matrix.Identity(), cam); const t = -ray.origin.z / ray.direction.z; return [ray.origin.x + ray.direction.x*t, ray.origin.y + ray.direction.y*t]; };
let drag = null;
for(const el of document.querySelectorAll('.atomi')) el.addEventListener('pointerdown', e => { e.preventDefault(); drag = { key: el.dataset.sp, id: e.pointerId };
  ghost.style.background = el.querySelector('.pallo').style.background; ghost.style.left = e.clientX + 'px'; ghost.style.top = e.clientY + 'px'; ghost.style.display = 'block'; });
window.addEventListener('pointermove', e => { if(!drag || e.pointerId !== drag.id) return; ghost.style.left = e.clientX + 'px'; ghost.style.top = e.clientY + 'px'; });
const endDrag = e => { if(!drag || e.pointerId !== drag.id) return; ghost.style.display = 'none';
  const overList = document.getElementById('lista').getBoundingClientRect(), inList = e.clientX >= overList.left && e.clientX <= overList.right && e.clientY >= overList.top && e.clientY <= overList.bottom;
  if(!inList && e.type === 'pointerup'){ const rc = canvas.getBoundingClientRect(), p = toPlane((e.clientX - rc.left) * (canvas.width / rc.width), (e.clientY - rc.top) * (canvas.height / rc.height));
    const W = halfW(), r = SPECIES[drag.key].radius; spawn(drag.key, Math.max(-W + r, Math.min(W - r, p[0])), Math.max(-HALF_H + r, Math.min(HALF_H - r, p[1]))); fmt(); }
  drag = null; };
window.addEventListener('pointerup', endDrag); window.addEventListener('pointercancel', endDrag);
window.gVesi = { spawn, mols, SPECIES, RULES, step, scene, cam, toPlane };   // for tests
})();
</script>
</body>
</html>
'''
page = page.replace('__SHADERS__', shaders)
os.makedirs(os.path.join(ROOT, 'vesi'), exist_ok=True)
io.open(os.path.join(ROOT, 'vesi', 'index.html'), 'w', encoding='utf-8', newline='').write(page.replace(NL, CRLF))
blocks = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', page, re.S)
io.open(os.path.join(ROOT, 'vesi', 'chk_vesi.js'), 'w', encoding='utf-8').write((NL + ';' + NL).join(blocks))   # the inline scripts alone, for node --check (gitignored)
print('WRITTEN vesi/index.html', len(page), 'chars, shaders', len(shaders))
