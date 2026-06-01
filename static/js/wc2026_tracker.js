
// ═══════════════════════════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════════════════════════
const IMG_BASE = "https://static.flashscore.com/res/image/data/";

const TEAMS = {
  "mexico":       {name:"Mexico",       img:"hv6zUUPq-IPF97VQ3.png", group:"A"},
  "south-africa": {name:"South Africa", img:"rVRaM7A6-xQxQqqtQ.png", group:"A"},
  "south-korea":  {name:"South Korea",  img:"G6sdC2S0-63aNArwB.png", group:"A"},
  "czech-republic":{name:"Czech Republic",img:"/static/img/rep-checa.jpg",      group:"A"},
  "switzerland":  {name:"Switzerland",  img:"buRKTH76-88LAtdNt.png", group:"B"},
  "canada":       {name:"Canada",       img:"bymI0wAN-EqLGVN18.png", group:"B"},
  "qatar":        {name:"Qatar",        img:"WEb3WvAN-UPMdbcD9.png", group:"B"},
  "bosnia":        {name:"Bosnia",        img:"WYjftaA6-Iyld3bDd.png",      group:"B"},
  "scotland":     {name:"Scotland",     img:"zknbF9U0-lfZlm1uk.png", group:"C"},
  "brazil":       {name:"Brazil",       img:"S4Kz1kjC-88LAtdNt.png", group:"C"},
  "haiti":        {name:"Haiti",        img:"d2aGgEQq-GY05WHbt.png", group:"C"},
  "morocco":      {name:"Morocco",      img:"r18xjQkC-hOurGDLS.png", group:"C"},
  "paraguay":     {name:"Paraguay",     img:"OMtYzrU0-I5qbBI7s.png", group:"D"},
  "usa":          {name:"USA",          img:"xfxMId8k-MPdHoKT3.png", group:"D"},
  "australia":    {name:"Australia",    img:"fJEGt1U0-YNb3oHYR.png", group:"D"},
  "turkey":        {name:"Turkey",        img:"buRKTH76-KtpTLRpL.png",      group:"D"},
  "germany":      {name:"Germany",      img:"0SofTgVH-fB4vYUZp.png", group:"E"},
  "ecuador":      {name:"Ecuador",      img:"nun1o8jC-IPF97VQ3.png", group:"E"},
  "ivory-coast":  {name:"Ivory Coast",  img:"dbwcq8A6-zTSy144G.png", group:"E"},
  "curacao":      {name:"Curacao",      img:"KSAOfD7k-dERAD3h1.png", group:"E"},
  "netherlands":  {name:"Netherlands",  img:"MkxaoTAN-fazrR153.png", group:"F"},
  "tunisia":      {name:"Tunisia",      img:"rZRftulC-67eTsYY5.png", group:"F"},
  "japan":        {name:"Japan",        img:"Y7SDT7T0-8toS1iya.png", group:"F"},
  "sweden":        {name:"Sweden",        img:"6eDtOume-fazrR153.png",       group:"F"},
  "belgium":      {name:"Belgium",      img:"AqUnTDAN-dtrVaP64.png", group:"G"},
  "egypt":        {name:"Egypt",        img:"SKagcEU0-j9fRtEHh.png", group:"G"},
  "iran":         {name:"Iran",         img:"0OVmBa6k-h2ICxBRT.png", group:"G"},
  "new-zealand":  {name:"New Zealand",  img:"jJWwg8S0-zmDbXBOa.png", group:"G"},
  "spain":        {name:"Spain",        img:"6eDtOume-0E8Iihe1.png", group:"H"},
  "uruguay":      {name:"Uruguay",      img:"pvtmslhT-WdZ4jMrq.png", group:"H"},
  "cape-verde":   {name:"Cape Verde",   img:"vRSce5lC-GvK8wiCN.png", group:"H"},
  "saudi-arabia": {name:"Saudi Arabia", img:"xIdEGDme-KtpTLRpL.png", group:"H"},
  "france":       {name:"France",       img:"04V6zbA6-U3HPIwDq.png", group:"I"},
  "norway":       {name:"Norway",       img:"vDNLLPme-8doAmYTm.png", group:"I"},
  "senegal":      {name:"Senegal",      img:"xORbTVT0-lQcLqf4g.png", group:"I"},
  "iraq":          {name:"Iraq",          img:"0OVmBa6k-h2ICxBRT.png",      group:"I"},
  "austria":      {name:"Austria",      img:"hO1wW196-6cnthjRG.png", group:"J"},
  "argentina":    {name:"Argentina",    img:"ObxjG3Rq-nBWCl0De.png", group:"J"},
  "algeria":      {name:"Algeria",      img:"A9ccQtU0-YFbDUeTh.png", group:"J"},
  "jordan":       {name:"Jordan",       img:"lC24EqiT-r5trb9zO.png", group:"J"},
  "portugal":     {name:"Portugal",     img:"Grhsr8gT-vZG58BBc.png", group:"K"},
  "colombia":     {name:"Colombia",     img:"Y70aXOTH-C6kVdO5F.png", group:"K"},
  "uzbekistan":   {name:"Uzbekistan",   img:"najJX2oe-MeuncTkU.png", group:"K"},
  "dr-congo":      {name:"DR Congo",      img:null,                         group:"K"},
  "croatia":      {name:"Croatia",      img:"GAQDu7jC-zXtZbqMA.png", group:"L"},
  "england":      {name:"England",      img:"lfoVvLPq-Iyld3bDd.png", group:"L"},
  "ghana":        {name:"Ghana",        img:"OzvG52Rq-8vfTQDSH.png", group:"L"},
  "panama":       {name:"Panama",       img:"WYjftaA6-6yXdouA1.png", group:"L"},
};

const GROUP_NAMES = ["A","B","C","D","E","F","G","H","I","J","K","L"];

const GROUPS = {
  A:["mexico","south-africa","south-korea","czech-republic"],
  B:["switzerland","canada","qatar","bosnia"],
  C:["scotland","brazil","haiti","morocco"],
  D:["paraguay","usa","australia","turkey"],
  E:["germany","ecuador","ivory-coast","curacao"],
  F:["netherlands","tunisia","japan","sweden"],
  G:["belgium","egypt","iran","new-zealand"],
  H:["spain","uruguay","cape-verde","saudi-arabia"],
  I:["france","norway","senegal","iraq"],
  J:["austria","argentina","algeria","jordan"],
  K:["portugal","colombia","uzbekistan","dr-congo"],
  L:["croatia","england","ghana","panama"],
};

// FIFA standard group stage matchday order: MD1=[0v1,2v3], MD2=[0v2,1v3], MD3=[0v3,1v2]
const PAIRINGS = [[0,1],[2,3],[0,2],[1,3],[0,3],[1,2]];
const MATCHDAY  = [1,    1,    2,    2,    3,    3];

// Approximate FIFA 2026 group stage dates (June 11 – July 2)
const GROUP_DATES = {
  A:["11 Jun","11 Jun","15 Jun","16 Jun","20 Jun","20 Jun"],
  B:["12 Jun","12 Jun","16 Jun","17 Jun","21 Jun","21 Jun"],
  C:["13 Jun","13 Jun","17 Jun","18 Jun","22 Jun","22 Jun"],
  D:["14 Jun","14 Jun","18 Jun","19 Jun","23 Jun","23 Jun"],
  E:["14 Jun","14 Jun","18 Jun","19 Jun","23 Jun","23 Jun"],
  F:["15 Jun","15 Jun","19 Jun","20 Jun","24 Jun","24 Jun"],
  G:["15 Jun","15 Jun","19 Jun","20 Jun","24 Jun","24 Jun"],
  H:["16 Jun","16 Jun","20 Jun","21 Jun","25 Jun","25 Jun"],
  I:["16 Jun","16 Jun","20 Jun","21 Jun","25 Jun","25 Jun"],
  J:["17 Jun","17 Jun","21 Jun","22 Jun","26 Jun","26 Jun"],
  K:["17 Jun","17 Jun","21 Jun","22 Jun","26 Jun","26 Jun"],
  L:["18 Jun","18 Jun","22 Jun","23 Jun","27 Jun","27 Jun"],
};

// Generate all 72 group-stage matches
const GROUP_MATCHES = [];
GROUP_NAMES.forEach(g => {
  const teams = GROUPS[g];
  PAIRINGS.forEach(([a,b], i) => {
    GROUP_MATCHES.push({
      id: `G${g}${i+1}`,
      group: g,
      phase: "group",
      matchday: MATCHDAY[i],
      date: GROUP_DATES[g][i],
      home: teams[a],
      away: teams[b],
    });
  });
});

// Knockout round slots
const KO_ROUNDS = [
  {id:"R32",  label:"Ronda de 32",     count:16},
  {id:"R16",  label:"Octavos de Final",count:8},
  {id:"QF",   label:"Cuartos de Final",count:4},
  {id:"SF",   label:"Semifinales",     count:2},
  {id:"FINAL",label:"Final",           count:1},
  {id:"3RD",  label:"3er Lugar",       count:1},
];

const KO_MATCHES = [];
KO_ROUNDS.forEach(r => {
  for(let i=1;i<=r.count;i++){
    KO_MATCHES.push({id:`${r.id}_${i}`, phase:r.id, slot:i, home:null, away:null});
  }
});

const ALL_MATCHES = [...GROUP_MATCHES, ...KO_MATCHES];

// ═══════════════════════════════════════════════════════════════════
// STATE  (localStorage key: "wc2026")
// ═══════════════════════════════════════════════════════════════════
function loadState(){ return JSON.parse(localStorage.getItem("wc2026")||"{}"); }
function saveState(s){ localStorage.setItem("wc2026",JSON.stringify(s)); }
function getMatch(id){ const s=loadState(); return s[id]||{home:null,away:null,status:"pending",events:[]}; }
function setMatch(id,d){ const s=loadState(); s[id]=d; saveState(s); }

// ═══════════════════════════════════════════════════════════════════
// STANDINGS
// ═══════════════════════════════════════════════════════════════════
function calcStandings(group){
  const stats={};
  GROUPS[group].forEach(t => stats[t]={team:t,MP:0,W:0,D:0,L:0,GF:0,GA:0,GD:0,Pts:0});
  GROUP_MATCHES.filter(m=>m.group===group).forEach(m=>{
    const d=getMatch(m.id);
    if(d.status!=="finished"||d.home===null||d.away===null) return;
    const [h,a]=[d.home,d.away];
    stats[m.home].MP++; stats[m.away].MP++;
    stats[m.home].GF+=h; stats[m.home].GA+=a;
    stats[m.away].GF+=a; stats[m.away].GA+=h;
    if(h>a){stats[m.home].W++;stats[m.away].L++;stats[m.home].Pts+=3;}
    else if(h<a){stats[m.away].W++;stats[m.home].L++;stats[m.away].Pts+=3;}
    else{stats[m.home].D++;stats[m.away].D++;stats[m.home].Pts++;stats[m.away].Pts++;}
  });
  Object.values(stats).forEach(s=>s.GD=s.GF-s.GA);
  return Object.values(stats).sort((a,b)=>b.Pts-a.Pts||b.GD-a.GD||b.GF-a.GF||a.team.localeCompare(b.team));
}

function calcAllThirds(){
  return GROUP_NAMES.map(g=>{
    const s=calcStandings(g);
    return {...s[2],group:g};
  }).sort((a,b)=>b.Pts-a.Pts||b.GD-a.GD||b.GF-a.GF||a.team.localeCompare(b.team));
}

function groupProgress(group){
  const total=GROUP_MATCHES.filter(m=>m.group===group).length;
  const done=GROUP_MATCHES.filter(m=>m.group===group&&getMatch(m.id).status==="finished").length;
  return {total,done};
}

// ═══════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════
function flag(teamId){
  const t=TEAMS[teamId];
  if(!t) return "";
  if(t.img){
    if(t.img.indexOf('/')!==-1) return `<img class="flag-img" src="${t.img}" alt="${t.name}" onerror="this.style.display='none'">`;
    return `<img class="flag-img" src="${IMG_BASE}${t.img}" alt="${t.name}" onerror="this.style.display='none'">`;
  }
  return `<span style="display:inline-block;width:20px;margin-right:5px;text-align:center">🏳️</span>`;
}
function tname(id){ return TEAMS[id]?.name||id||"?"; }

// ═══════════════════════════════════════════════════════════════════
// RENDER — GROUPS
// ═══════════════════════════════════════════════════════════════════
function renderGroups(){
  document.getElementById("groups-container").innerHTML = GROUP_NAMES.map(g=>{
    const standings=calcStandings(g);
    const {total,done}=groupProgress(g);
    const rows=standings.map((s,i)=>{
      const cls=i<2?"rank-playoff":i===2?"rank-third":"rank-out";
      const gd=(s.GD>0?"+":"")+s.GD;
      return `<tr>
        <td><span class="rank-badge ${cls}">${i+1}</span></td>
        <td class="left">${flag(s.team)}${tname(s.team)}</td>
        <td>${s.MP}</td><td>${s.W}</td><td>${s.D}</td><td>${s.L}</td>
        <td>${s.GF}:${s.GA}</td><td>${gd}</td><td><b>${s.Pts}</b></td>
      </tr>`;
    }).join("");
    // build numeric inputs per team for quick edit + save button
    const teams = GROUPS[g];
    const estado = JSON.parse(localStorage.getItem('estado_wchtml_matches')||'{}');
    const locked = estado.lockedGroup || null;
    const savedGroup = estado.groups && estado.groups[g] ? estado.groups[g] : {};
    const matchesForGroup = GROUP_MATCHES.filter(m=>m.group===g);
    const inputsHtml = teams.map(t=>{
      const savedVal = savedGroup[t];
      const goals = (savedVal && typeof savedVal==='object') ? (savedVal.goals!==undefined?savedVal.goals:'') : (savedVal!==undefined?savedVal:'');
      const selMatch = (savedVal && typeof savedVal==='object') ? (savedVal.match||'') : '';
      const disabled = locked && locked!==g ? 'disabled' : '';
      const matchOptions = ['<option value="">— Seleccionar partido —</option>', ...matchesForGroup.map(m=>{
        const label = `${m.id} ${tname(m.home)||''} vs ${tname(m.away)||''}`;
        const sel = selMatch===m.id? 'selected' : '';
        return `<option value="${m.id}" ${sel}>${label}</option>`;
      })].join('');
      return `<div style="display:flex;align-items:center;gap:8px;margin:6px 0">
        <div style="min-width:120px;color:#cbd5e1">${tname(t)}</div>
        <label style="color:#94a3b8;font-size:.8rem;margin-right:6px">Goles</label>
        <input class="group-score-inp" data-group="${g}" data-team="${t}" type="number" min="0" value="${goals}" ${disabled} style="width:72px;padding:6px;border-radius:6px;border:1px solid #2e2e4e;background:#0b0b13;color:#e2e8f0">
        <label style="color:#94a3b8;font-size:.8rem;margin:0 6px">Partido</label>
        <select class="group-match-select" data-group="${g}" data-team="${t}" ${disabled} style="padding:6px;border-radius:6px;border:1px solid #2e2e4e;background:#0b0b13;color:#e2e8f0">${matchOptions}</select>
      </div>`;
    }).join('');

    return `<div class="group-card">
      <div class="group-card-header">Grupo ${g}
        <span class="group-progress">${done}/${total} jugados</span>
      </div>
      <table>
        <thead><tr>
          <th>#</th><th class="left">Equipo</th>
          <th title="Partidos Jugados">PJ</th><th title="Victorias">V</th>
          <th title="Empates">E</th><th title="Derrotas">D</th>
          <th title="Goles">G</th><th title="Diferencia de goles">DG</th>
          <th title="Puntos">Pts</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="padding:10px;background:#151526;border-top:1px solid #232332;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:260px">${inputsHtml}</div>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          <button class="btn" title="Guardar grupo ${g} (bloquear otros)" onclick="saveGroupFromCard('${g}')">💾 Guardar Grupo ${g}</button>
          <button class="btn btn-outline" onclick="loadGroupFromCard('${g}')">🔃 Cargar guardado</button>
        </div>
      </div>
    </div>`;
  }).join("");
}

// Save group inputs into grouped JSON and lock other groups
function saveGroupFromCard(group){
  const inputs = Array.from(document.querySelectorAll(`input.group-score-inp[data-group="${group}"]`));
  const selects = Array.from(document.querySelectorAll(`select.group-match-select[data-group="${group}"]`));
  const obj = {};
  const key = 'estado_wchtml_matches';
  const estado = JSON.parse(localStorage.getItem(key)||'{}');
  estado.groups = estado.groups||{};
  estado.events = estado.events||[];
  const when = new Date().toISOString();
  inputs.forEach(i=>{
    const team = i.dataset.team;
    const sel = selects.find(s=>s.dataset.team===team);
    const matchId = sel? sel.value || null : null;
    const v = i.value!==''?parseInt(i.value):null;
    obj[team] = {goals: v, match: matchId};
    // if match specified, update that match score in stored matches
    if(matchId && v!==null){
      const m = ALL_MATCHES.find(x=>x.id===matchId);
      if(m){
        const d = getMatch(matchId);
        if(m.home===team) d.home = v;
        else if(m.away===team) d.away = v;
        setMatch(matchId,d);
      }
    }
    // add event for this team save
    estado.events.push({group,team,match:matchId,goals:v,when,source:'ui-save'});
  });
  estado.groups[group]=obj;
  estado.lockedGroup = group;
  localStorage.setItem(key,JSON.stringify(estado));
  // re-render to reflect match changes and locks
  renderMatchCards();
  renderGroups();
  renderStats();
  updateBracket();
  updateSummary();
  alert('✅ Estado del Grupo '+group+' guardado; partidos y UI actualizados, otros grupos bloqueados.');
}

function loadGroupFromCard(group){
  const key = 'estado_wchtml_matches';
  const estado = JSON.parse(localStorage.getItem(key)||'{}');
  const data = estado.groups && estado.groups[group];
  if(!data){ alert('No hay datos guardados para Grupo '+group); return; }
  Object.keys(data).forEach(team=>{
    const el = document.querySelector(`input.group-score-inp[data-group="${group}"][data-team="${team}"]`);
    const sel = document.querySelector(`select.group-match-select[data-group="${group}"][data-team="${team}"]`);
    const val = data[team];
    if(el) el.value = val && val.goals!==undefined && val.goals!==null ? val.goals : '';
    if(sel) sel.value = val && val.match? val.match : '';
  });
  alert('✅ Grupo '+group+' cargado en la UI');
}

// ═══════════════════════════════════════════════════════════════════
// RENDER — MATCHES
// ═══════════════════════════════════════════════════════════════════
let activeMatchGroup = "A";

function renderMatchTabs(){
  const groups=["ALL",...GROUP_NAMES];
  document.getElementById("match-group-tabs").innerHTML = groups.map(g=>
    `<button class="gtab ${g===activeMatchGroup?"active":""}" onclick="switchMatchGroup('${g}')">${g==="ALL"?"Todos":"Grupo "+g}</button>`
  ).join("");
}

function switchMatchGroup(g){
  activeMatchGroup=g;
  renderMatchTabs();
  renderMatchCards();
}

function renderMatchCards(){
  const matches = activeMatchGroup==="ALL" ? GROUP_MATCHES : GROUP_MATCHES.filter(m=>m.group===activeMatchGroup);
  document.getElementById("matches-container").innerHTML = matches.map(m=>{
    const d=getMatch(m.id);
    const hv=d.home!==null?d.home:"";
    const av=d.away!==null?d.away:"";
    const statusOpts=["pending","playing","finished"].map(s=>
      `<option value="${s}" ${s===d.status?"selected":""}>${({'pending':"⏳ Pendiente","playing":"🔴 En juego","finished":"✅ Finalizado"})[s]}</option>`
    ).join("");
    return `<div class="match-card" id="mc_${m.id}">
      <div class="match-meta">
        <span>Grupo ${m.group}</span>
        <span>MD${m.matchday}</span>
        <span>${m.date}</span>
      </div>
      <div class="match-team">${flag(m.home)}<span>${tname(m.home)}</span></div>
      <div class="match-score-block">
        <input type="number" class="score-inp" id="sh_${m.id}" min="0" max="99" value="${hv}" placeholder="—">
        <span class="score-sep">:</span>
        <input type="number" class="score-inp" id="sa_${m.id}" min="0" max="99" value="${av}" placeholder="—">
      </div>
      <div class="match-team away"><span>${tname(m.away)}</span>${flag(m.away)}</div>
      <div class="match-actions">
        <select class="status-sel" onchange="changeStatus('${m.id}',this.value)">${statusOpts}</select>
        <div style="display:flex;gap:5px">
          <button class="btn-save" id="bs_${m.id}" onclick="saveScore('${m.id}')">Guardar</button>
          <button class="btn-detail" onclick="openDetail('${m.id}')">+ Detalle</button>
        </div>
      </div>
    </div>`;
  }).join("");
}

function saveScore(matchId){
  const hEl=document.getElementById(`sh_${matchId}`);
  const aEl=document.getElementById(`sa_${matchId}`);
  const h=hEl.value!==""?parseInt(hEl.value):null;
  const a=aEl.value!==""?parseInt(aEl.value):null;
  const d=getMatch(matchId);
  d.home=h; d.away=a;
  setMatch(matchId,d);
  // after updating a match, also persist grouped estado JSON
  saveEstadoLocal();
  renderGroups();
  renderStats();
  updateBracket();
  updateSummary();
  const btn=document.getElementById(`bs_${matchId}`);
  if(btn){btn.textContent="✓";btn.classList.add("saved");setTimeout(()=>{btn.textContent="Guardar";btn.classList.remove("saved");},1200);}
}

function changeStatus(matchId,status){
  const d=getMatch(matchId);
  d.status=status;
  setMatch(matchId,d);
  renderGroups();
  renderStats();
  updateBracket();
  updateSummary();
}

// ═══════════════════════════════════════════════════════════════════
// RENDER — BRACKET
// ═══════════════════════════════════════════════════════════════════
// R32 slot pairings using group positions.
// Format: ["1A","2B"] means winner group A vs runner-up group B.
// Official FIFA 2026 bracket draw hasn't been published → positional placeholder.
const R32_PAIRINGS = [
  ["1A","2B"],["1C","2D"],["1E","2F"],["1G","2H"],
  ["1I","2J"],["1K","2L"],["1B","2A"],["1D","2C"],
  ["1F","2E"],["1H","2G"],["1J","2I"],["1L","2K"],
  ["T1","T2"],["T3","T4"],["T5","T6"],["T7","T8"],
];

function resolvePos(slot){
  if(slot.startsWith("T")){
    const n=parseInt(slot.slice(1))-1;
    return calcAllThirds()[n]?.team||null;
  }
  const pos=parseInt(slot[0])-1;
  const grp=slot.slice(1);
  return calcStandings(grp)[pos]?.team||null;
}

function updateBracket(){
  const container=document.getElementById("bracket-container");
  const rounds=[
    {id:"R32",label:"Ronda de 32"},
    {id:"R16",label:"Octavos"},
    {id:"QF",label:"Cuartos"},
    {id:"SF",label:"Semifinales"},
    {id:"FINAL",label:"Final"},
    {id:"3RD",label:"3er Lugar"},
  ];

  container.innerHTML = rounds.map(r=>{
    let slots;
    if(r.id==="R32"){
      slots=R32_PAIRINGS.map(([p0,p1],i)=>{
        const hId=resolvePos(p0);
        const aId=resolvePos(p1);
        const d=getMatch(`R32_${i+1}`);
        return bMatch(`R32_${i+1}`,hId||p0,aId||p1,hId,aId,d,true);
      });
    } else {
      slots=KO_MATCHES.filter(m=>m.phase===r.id).map(m=>{
        const d=getMatch(m.id);
        const hDisp=m.home?tname(m.home):`Slot ${m.slot}A`;
        const aDisp=m.away?tname(m.away):`Slot ${m.slot}B`;
        return bMatch(m.id,hDisp,aDisp,m.home,m.away,d,true);
      });
    }
    return `<div class="bracket-round">
      <div class="bracket-round-title">${r.label}</div>
      ${slots.join("")}
    </div>`;
  }).join("");
}

function bMatch(id,hDisp,aDisp,hId,aId,d,clickable){
  const hs=d.home!==null?d.home:"-";
  const as=d.away!==null?d.away:"-";
  const hWin=d.status==="finished"&&d.home!==null&&d.away!==null&&d.home>d.away;
  const aWin=d.status==="finished"&&d.home!==null&&d.away!==null&&d.away>d.home;
  const onclick=clickable?`onclick="openKODetail('${id}',${JSON.stringify(hDisp)},${JSON.stringify(aDisp)},${JSON.stringify(hId)},${JSON.stringify(aId)})"` :"";
  return `<div class="bracket-match" ${onclick}>
    <div class="b-team ${hWin?"winner":""}">
      ${hId?flag(hId):"🏳️ "}<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis">${hDisp}</span>
      <span class="b-score">${hs}</span>
    </div>
    <div class="b-team ${aWin?"winner":""}">
      ${aId?flag(aId):"🏳️ "}<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis">${aDisp}</span>
      <span class="b-score">${as}</span>
    </div>
  </div>`;
}

// ═══════════════════════════════════════════════════════════════════
// DETAIL MODAL (group matches)
// ═══════════════════════════════════════════════════════════════════
let currentDetailId=null;

function openDetail(matchId){
  currentDetailId=matchId;
  const m=GROUP_MATCHES.find(x=>x.id===matchId);
  if(!m) return;
  _renderModal(matchId,m.home,m.away,tname(m.home),tname(m.away));
}

function openKODetail(matchId,hDisp,aDisp,hId,aId){
  currentDetailId=matchId;
  _renderModal(matchId,hId,aId,hDisp,aDisp);
}

function _renderModal(matchId,homeId,awayId,homeName,awayName){
  const d=getMatch(matchId);
  const events=d.events||[];
  document.getElementById("modal-title").innerHTML =
    `${homeId?flag(homeId):""}<b>${homeName}</b> vs <b>${awayName}</b>${awayId?flag(awayId):""}`;

  const evHtml = events.length===0
    ? `<p style="color:#6b7280;font-size:.82rem;padding:8px 0">Sin eventos registrados.</p>`
    : events.map((e,i)=>`<div class="event-item">
        <span class="min-badge">${e.min||0}'</span>
        <span>${e.type==="goal"?"⚽":e.type==="yellow"?"🟨":"🟥"}</span>
        <span style="flex:1">${e.player||"Jugador"} <span style="color:#a78bfa">(${tname(e.team)})</span></span>
        <button onclick="removeEvent('${matchId}',${i})" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:.85rem">✕</button>
      </div>`).join("");

  const teamOpts=[homeId,awayId].filter(Boolean).map(t=>
    `<option value="${t}">${tname(t)}</option>`).join("");

  document.getElementById("modal-body").innerHTML=`
    <div style="margin-bottom:14px">
      <b style="color:#c4b5fd;font-size:.9rem">Agregar evento</b>
      <div class="form-row" style="margin-top:8px">
        <select id="ev-type">
          <option value="goal">⚽ Gol</option>
          <option value="yellow">🟨 Amarilla</option>
          <option value="red">🟥 Roja</option>
        </select>
        <input type="number" id="ev-min" min="1" max="120" placeholder="Min">
        <input type="text" id="ev-player" placeholder="Nombre del jugador" style="flex:1;min-width:120px">
        <select id="ev-team">${teamOpts}</select>
      </div>
      <button class="btn" style="font-size:.82rem;padding:7px 14px" onclick="addEvent('${matchId}','${homeId}','${awayId}')">➕ Agregar</button>
    </div>
    <div>${evHtml}</div>
  `;
  document.getElementById("detail-modal").classList.add("open");
}

function addEvent(matchId,homeId,awayId){
  const type=document.getElementById("ev-type").value;
  const min=parseInt(document.getElementById("ev-min").value)||0;
  const player=document.getElementById("ev-player").value.trim();
  const team=document.getElementById("ev-team").value;
  if(!player&&type==="goal"){alert("Ingresa el nombre del jugador.");return;}
  const d=getMatch(matchId);
  if(!d.events) d.events=[];
  d.events.push({type,min,player,team});
  d.events.sort((a,b)=>a.min-b.min);
  setMatch(matchId,d);
  _renderModal(matchId,homeId,awayId,tname(homeId)||"?",tname(awayId)||"?");
  renderStats();
}

function removeEvent(matchId,index){
  const d=getMatch(matchId);
  d.events.splice(index,1);
  setMatch(matchId,d);
  // Re-open modal — need original teams
  const m=GROUP_MATCHES.find(x=>x.id===matchId)||KO_MATCHES.find(x=>x.id===matchId);
  if(m){_renderModal(matchId,m.home,m.away,tname(m.home||""),tname(m.away||""));}
  renderStats();
}

function closeModal(){
  document.getElementById("detail-modal").classList.remove("open");
}

// ═══════════════════════════════════════════════════════════════════
// RENDER — STATS
// ═══════════════════════════════════════════════════════════════════
function renderStats(){
  const state=loadState();
  const goals={},cards={},teamGF={};

  Object.values(state).forEach(d=>{
    (d.events||[]).forEach(e=>{
      const k=`${e.player||"?"}|${e.team}`;
      if(e.type==="goal"){
        goals[k]=(goals[k]||0)+1;
        teamGF[e.team]=(teamGF[e.team]||0)+1;
      } else {
        const ck=`${k}|${e.type}`;
        cards[ck]=(cards[ck]||0)+1;
      }
    });
  });

  const noData=`<tr><td colspan="3" style="color:#6b7280;text-align:center;padding:14px">Sin datos</td></tr>`;

  // Goals
  const gRows=Object.entries(goals).sort(([,a],[,b])=>b-a).slice(0,15).map(([k,n])=>{
    const [player,teamId]=k.split("|");
    return `<tr><td>${flag(teamId)}</td><td>${player}</td><td style="text-align:right"><b>${n} ⚽</b></td></tr>`;
  }).join("")||noData;
  document.getElementById("stats-goals").innerHTML=
    `<table><thead><tr><th></th><th class="left">Jugador</th><th>Goles</th></tr></thead><tbody>${gRows}</tbody></table>`;

  // Cards
  const cRows=Object.entries(cards).sort(([,a],[,b])=>b-a).slice(0,15).map(([k,n])=>{
    const [player,teamId,type]=k.split("|");
    return `<tr><td>${flag(teamId)}</td><td>${player}</td><td style="text-align:right">${type==="yellow"?"🟨":"🟥"} ×${n}</td></tr>`;
  }).join("")||noData;
  document.getElementById("stats-cards").innerHTML=
    `<table><thead><tr><th></th><th class="left">Jugador</th><th>Tarjetas</th></tr></thead><tbody>${cRows}</tbody></table>`;

  // Teams GF
  const tRows=Object.entries(teamGF).sort(([,a],[,b])=>b-a).slice(0,12).map(([t,n])=>
    `<tr><td>${flag(t)}</td><td>${tname(t)}</td><td style="text-align:right"><b>${n}</b></td></tr>`
  ).join("")||noData;
  document.getElementById("stats-teams-gf").innerHTML=
    `<table><thead><tr><th></th><th class="left">Equipo</th><th>Goles</th></tr></thead><tbody>${tRows}</tbody></table>`;

  // Thirds ranking
  const thirds=calcAllThirds();
  const trdRows=thirds.map((s,i)=>
    `<tr><td>${i+1}</td><td class="left">${flag(s.team)}${tname(s.team)}</td><td>${s.Pts}</td><td>${s.GD>=0?"+":""}${s.GD}</td><td>${s.GF}</td></tr>`
  ).join("");
  document.getElementById("stats-thirds").innerHTML=
    `<table><thead><tr><th>#</th><th class="left">Equipo</th><th>Pts</th><th>DG</th><th>GF</th></tr></thead><tbody>${trdRows}</tbody></table>`;
}

// ═══════════════════════════════════════════════════════════════════
// EXPORT / IMPORT
// ═══════════════════════════════════════════════════════════════════
function exportCSV(){
  const rows=["partido_id,grupo,fase,jornada,fecha,local,visitante,goles_local,goles_visitante,estado"];
  ALL_MATCHES.forEach(m=>{
    const d=getMatch(m.id);
    rows.push([
      m.id, m.group||"", m.phase, m.matchday||"", m.date||"",
      tname(m.home||""), tname(m.away||""),
      d.home!==null?d.home:"",
      d.away!==null?d.away:"",
      d.status
    ].map(v=>`"${v}"`).join(","));
  });
  dlFile("resultados_wc2026.csv",rows.join("\n"),"text/csv");
}

function exportStandings(){
  const rows=["grupo,pos,equipo,PJ,V,E,D,GF,GA,DG,Pts"];
  GROUP_NAMES.forEach(g=>{
    calcStandings(g).forEach((s,i)=>{
      rows.push([g,i+1,tname(s.team),s.MP,s.W,s.D,s.L,s.GF,s.GA,s.GD,s.Pts].map(v=>`"${v}"`).join(","));
    });
  });
  dlFile("standings_wc2026.csv",rows.join("\n"),"text/csv");
}

function exportEvents(){
  const rows=["partido_id,grupo,local,visitante,tipo,jugador,equipo,minuto"];
  ALL_MATCHES.forEach(m=>{
    const d=getMatch(m.id);
    (d.events||[]).forEach(e=>{
      rows.push([m.id,m.group||"",tname(m.home||""),tname(m.away||""),e.type,e.player||"",tname(e.team),e.min]
        .map(v=>`"${v}"`).join(","));
    });
  });
  dlFile("eventos_wc2026.csv",rows.join("\n"),"text/csv");
}

function importCSV(input){
  const file=input.files[0];
  if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    const lines=e.target.result.split("\n").slice(1);
    let count=0;
    lines.forEach(line=>{
      if(!line.trim()) return;
      const cols=line.split(",").map(c=>c.replace(/^"|"$/g,"").trim());
      // Expected: partido_id, grupo, fase, jornada, fecha, local, visitante, goles_local, goles_visitante, estado
      if(cols.length<10) return;
      const [id,,,,,,,hGoal,aGoal,status]=cols;
      const h=hGoal!==""?parseInt(hGoal):null;
      const a=aGoal!==""?parseInt(aGoal):null;
      const d=getMatch(id);
      d.home=h; d.away=a; d.status=status||"pending";
      setMatch(id,d);
      count++;
    });
    alert(`✅ ${count} partidos importados.`);
    renderAll();
    input.value="";
  };
  reader.readAsText(file);
}

function dlFile(filename,content,type){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([content],{type}));
  a.download=filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function resetAll(){
  if(!confirm("⚠️ ¿Seguro que deseas eliminar TODOS los resultados y eventos del torneo?\n\nEsta acción no se puede deshacer.")) return;
  localStorage.removeItem("wc2026");
  renderAll();
}

// ═══════════════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════════════
function updateSummary(){
  const state=loadState();
  const ids=Object.keys(state);
  const finished=ids.filter(id=>state[id].status==="finished").length;
  const playing=ids.filter(id=>state[id].status==="playing").length;
  const totalEvents=ids.reduce((acc,id)=>acc+(state[id].events?.length||0),0);
  document.getElementById("summary-info").innerHTML=`
    Partidos registrados: <b style="color:#e2e8f0">${ids.length}</b><br>
    Partidos finalizados: <b style="color:#4ade80">${finished}</b><br>
    En juego: <b style="color:#fb923c">${playing}</b><br>
    Total de eventos: <b style="color:#e2e8f0">${totalEvents}</b><br>
    Grupos totales: <b style="color:#e2e8f0">12</b><br>
    Equipos: <b style="color:#e2e8f0">48</b><br>
    Partidos de fase de grupos: <b style="color:#e2e8f0">72</b>
  `;
}

// ═══════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════
function showTab(tab,btn){
  document.querySelectorAll(".tab-content").forEach(el=>el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(el=>el.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
  if(btn) btn.classList.add("active");
  if(tab==="partidos"){
    renderMatchTabs();
    renderMatchCards();
  }
  if(tab==="bracket") updateBracket();
  if(tab==="stats") renderStats();
  if(tab==="datos") updateSummary();
}

// ═══════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════
function renderAll(){
  renderGroups();
  renderMatchTabs();
  renderMatchCards();
  updateBracket();
  renderStats();
  updateSummary();
}

renderGroups(); // initial render (grupos tab is active)