(function(){
"use strict";
const $=s=>document.querySelector(s);
const SRC={mptenders:"MP Tenders",rajasthan:"Rajasthan eProc",gem:"GeM"};
let ALL=[],META={},VIEW=[],SHOWN=0;const PAGE=40;
const now=new Date();
const pd=s=>{if(!s)return null;const m=s.match(/(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/);return m?new Date(+m[1],m[2]-1,+m[3],+m[4],+m[5]):null};
// times in the data are India time; convert "now" to IST wall clock for comparisons
const istNow=()=>{const d=new Date();return new Date(d.getTime()+d.getTimezoneOffset()*60000+330*60000)};
const fmtD=d=>d?d.toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})+" "+d.toLocaleTimeString("en-IN",{hour:"numeric",minute:"2-digit"}):"—";
const rs=n=>"₹"+Number(n).toLocaleString("en-IN",{maximumFractionDigits:0});
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const daysLeft=t=>{const c=pd(t.closing);return c?(c-istNow())/864e5:null};
const isNew=t=>{const f=pd(t.first_seen);return f&&(istNow()-f)/864e5<=2};
const soonDays=()=>+(META.closing_soon_days||3);

function opt(sel,vals,all){sel.innerHTML=(all?`<option value="">${all}</option>`:"")+vals.map(v=>`<option value="${esc(v[0])}">${esc(v[1])}</option>`).join("")}

function readHash(){const p=new URLSearchParams(location.hash.slice(1));return p}
function writeHash(){const p=new URLSearchParams();for(const k of["q","cat","state","dist","src","show","sort"]){const v=$("#"+k).value;if(v&&!(k==="show"&&v==="open")&&!(k==="sort"&&v==="new")&&!(k==="cat"&&v===META.grocery_name))p.set(k,v)}if($("#cat").value==="")p.set("cat","*");history.replaceState(null,"","#"+p.toString())}

function counts(){const o=ALL.filter(t=>t.status==="open");return{open:o.length,g:o.filter(t=>t.cats.includes(META.grocery_name)),}}

function init(){
  const g=META.grocery_name||"Grocery";
  const open=ALL.filter(t=>t.status==="open");
  const catCount=c=>open.filter(t=>t.cats.includes(c)).length;
  opt($("#cat"),[...(META.categories||[g]).map(c=>[c,`${c} (${catCount(c)})`])],"All categories");
  const states=[...new Set(ALL.map(t=>t.state))].sort();
  opt($("#state"),states.map(s=>[s,s]),"All states");
  fillDistricts();
  const p=readHash();
  $("#cat").value=p.get("cat")==="*"?"":(p.get("cat")||g);
  for(const k of["q","state","src","show","sort"]) if(p.get(k)) $("#"+k).value=p.get(k);
  fillDistricts(); if(p.get("dist")) $("#dist").value=p.get("dist");
  // header
  const u=pd(META.updated);
  $("#updated").textContent="Updated "+(u?fmtD(u):"—")+" · checks every 3 hours";
  $("#srcs").innerHTML=["mptenders","rajasthan","gem"].map(k=>{const s=(META.sources||{})[k];if(!s)return`<span class="chip bad" title="No data yet">${SRC[k]}: no data yet</span>`;
     const n=(META.open_by_source||{})[k]||0;let txt=`${SRC[k]} · ${n.toLocaleString("en-IN")}`;let ok=s.ok;
     if(k==="gem"&&s.data_from){const d=new Date(s.data_from);const ageH=(Date.now()-d)/36e5;txt+=` · ${ageH<24?Math.round(ageH)+"h old":Math.round(ageH/24)+"d old"}`;if(ageH>24)ok=false}
     return`<span class="chip ${ok?"ok":"bad"}" title="${esc(s.error||"")}">${txt}</span>`}).join("");
  const gopen=open.filter(t=>t.cats.includes(g));
  $("#stats").innerHTML=`
   <div class="stat g" data-go="grocery"><b>${gopen.length.toLocaleString("en-IN")}</b><span>${esc(g)} tenders open</span></div>
   <div class="stat n" data-go="new"><b>${gopen.filter(isNew).length}</b><span>New ${esc(g.toLowerCase())} (2 days)</span></div>
   <div class="stat s" data-go="soon"><b>${gopen.filter(t=>{const d=daysLeft(t);return d!=null&&d>=0&&d<=soonDays()}).length}</b><span>Closing in ${soonDays()} days</span></div>
   <div class="stat h" data-go="all"><b>${open.length.toLocaleString("en-IN")}</b><span>All open tenders</span></div>`;
  document.querySelectorAll(".stat").forEach(el=>el.onclick=()=>{const go=el.dataset.go;$("#q").value="";$("#state").value="";$("#src").value="";$("#dist").value="";
    if(go==="all"){$("#cat").value="";$("#show").value="open"}else{$("#cat").value=g;$("#show").value=go==="grocery"?"open":go}apply()});
  for(const k of["cat","state","dist","src","show","sort"]) $("#"+k).onchange=()=>{if(k==="state")fillDistricts();apply()};
  let tm;$("#q").oninput=()=>{clearTimeout(tm);tm=setTimeout(apply,180)};
  $("#reset").onclick=()=>{$("#q").value="";$("#cat").value=g;$("#state").value="";fillDistricts();$("#dist").value="";$("#src").value="";$("#show").value="open";$("#sort").value="new";apply()};
  $("#more").onclick=()=>render(false);
  apply();
}
function fillDistricts(){const st=$("#state").value,cur=$("#dist").value;const ds={};ALL.forEach(t=>{if(t.status!=="open"||(st&&t.state!==st))return;(t.districts||["Unknown"]).forEach(d=>ds[d]=(ds[d]||0)+1)});
  const list=Object.keys(ds).sort((a,b)=>a==="Unknown"?1:b==="Unknown"?-1:a.localeCompare(b));opt($("#dist"),list.map(d=>[d,`${d} (${ds[d]})`]),"All districts");if(ds[cur])$("#dist").value=cur}

function apply(){
  const q=$("#q").value.trim().toLowerCase(),cat=$("#cat").value,st=$("#state").value,di=$("#dist").value,src=$("#src").value,show=$("#show").value,sort=$("#sort").value;
  const words=q.split(/\s+/).filter(Boolean);
  VIEW=ALL.filter(t=>{
    if(show==="closed"){if(t.status!=="closed")return false}else if(show!=="all"&&t.status!=="open")return false;
    if(show==="new"&&!isNew(t))return false;
    if(show==="soon"){const d=daysLeft(t);if(d==null||d<0||d>soonDays())return false}
    if(show==="near"&&!t.near)return false;
    if(cat&&!t.cats.includes(cat))return false;
    if(st&&t.state!==st)return false; if(src&&t.source!==src)return false;
    if(di&&!(t.districts||[]).includes(di))return false;
    if(words.length){const h=t._h||(t._h=[t.title,t.org,t.id,t.ref,(t.districts||[]).join(" "),t.location,t.state,t.description,t.product_category,(t.cats||[]).join(" ")].join(" ").toLowerCase());if(!words.every(w=>h.includes(w)))return false}
    return true});
  const cl=t=>t.closing||"9999";
  const sorters={closing:(a,b)=>cl(a).localeCompare(cl(b)),new:(a,b)=>(b.first_seen||"").localeCompare(a.first_seen||"")||(b.near-a.near)||cl(a).localeCompare(cl(b)),value:(a,b)=>(b.value||0)-(a.value||0)||cl(a).localeCompare(cl(b)),near:(a,b)=>(b.near-a.near)||cl(a).localeCompare(cl(b))};
  VIEW.sort(sorters[sort]||sorters.new);
  $("#count").textContent=`${VIEW.length.toLocaleString("en-IN")} tender${VIEW.length===1?"":"s"}`;
  writeHash(); render(true);
}
function card(t){
  const g=META.grocery_name;const d=daysLeft(t);const c=pd(t.closing);
  const b=[`<span class="b src">${SRC[t.source]}</span>`];
  if(t.status==="closed")b.push(`<span class="b closed">Closed</span>`);
  if(isNew(t)&&t.status==="open")b.push(`<span class="b new">NEW</span>`);
  if(d!=null&&d>=0&&d<=soonDays()){const n=istNow();const dd=Math.round((new Date(c.getFullYear(),c.getMonth(),c.getDate())-new Date(n.getFullYear(),n.getMonth(),n.getDate()))/864e5);b.push(`<span class="b soon">Closing ${dd<=0?"today":dd===1?"tomorrow":"in "+dd+" days"}</span>`)}
  if(t.near)b.push(`<span class="b near">📍 Near you</span>`);
  (t.cats||[]).forEach(x=>b.push(`<span class="b cat">${esc(x)}</span>`));
  if(t.mixed)b.push(`<span class="b mixed">mixed</span>`);
  const meta=[`<span>📍 <b>${esc((t.districts||["Unknown"]).join(", "))}</b>, ${esc(t.state)}</span>`,`<span>⏰ Closes <b>${fmtD(c)}</b></span>`];
  if(t.value)meta.push(`<span>Value <b>${rs(t.value)}</b></span>`);
  if(t.emd)meta.push(`<span>EMD <b>${rs(t.emd)}</b></span>`);
  if(t.quantity)meta.push(`<span>Qty <b>${Number(t.quantity).toLocaleString("en-IN")}</b></span>`);
  if(t.tender_category)meta.push(`<span>${esc(t.tender_category)}</span>`);
  const fl=(t.flags||[]).filter(f=>!/^EMD/.test(f)).map(f=>`<span class="flag">⚠ ${esc(f)}</span>`).join("");
  const hits=t.hits&&t.hits[g]?`<div class="hits">Matched: ${esc(t.hits[g].join(", "))}</div>`:"";
  const hint=t.hint&&t.hint.length?`<div class="hits">GeM search also found: ${esc(t.hint.join(", "))} — may be further down the item list, check the bid</div>`:"";
  const desc=t.description&&t.description!==t.title?`<div class="hits">${esc(t.description.slice(0,220))}</div>`:"";
  const open=t.source==="gem"?`<a class="btn" href="${esc(t.url)}" target="_blank" rel="noopener">Open bid document</a>`:`<a class="btn" href="${esc(t.url)}" target="_blank" rel="noopener">Open ${SRC[t.source]}</a>`;
  return `<article class="card t"><div class="badges">${b.join("")}</div><h3>${esc(t.title)}</h3><p class="org">${esc(t.org)}</p>
   <div class="meta">${meta.join("")}</div>${fl?`<div class="flags">${fl}</div>`:""}${hits}${hint}${desc}
   <div class="actions">${open}<button class="btn sec" data-copy="${esc(t.id)}">Copy ID</button><span class="id">${esc(t.id)}</span></div>
   ${t.source!=="gem"?`<div class="note">On the portal, paste the Tender ID in the search box (top left).</div>`:""}</article>`;
}
function render(reset){
  if(reset){SHOWN=0;$("#list").innerHTML=""}
  const part=VIEW.slice(SHOWN,SHOWN+PAGE);SHOWN+=part.length;
  if(!VIEW.length)$("#list").innerHTML=`<div class="card empty">No tenders match these filters.</div>`;
  else $("#list").insertAdjacentHTML("beforeend",part.map(card).join(""));
  $("#more").hidden=SHOWN>=VIEW.length;$("#more").textContent=`Show more (${(VIEW.length-SHOWN).toLocaleString("en-IN")} left)`;
}
document.addEventListener("click",e=>{const c=e.target.closest("[data-copy]");if(!c)return;navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy);const t=$("#toast");t.textContent="Copied "+c.dataset.copy;t.hidden=false;setTimeout(()=>t.hidden=true,1600)});
const fmtUpd=s=>{const d=pd(s);return d?d.toLocaleString("en-IN",{day:"numeric",month:"short",hour:"numeric",minute:"2-digit"})+" IST":s};
// ---------- login + decryption (all in this browser; the server only has encrypted files) ----------
const TE=new TextEncoder();
const b64d=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const b64e=u=>{let s="";u.forEach(b=>s+=String.fromCharCode(b));return btoa(s)};
const SKEY="ts_login";
const hex=buf=>[...new Uint8Array(buf)].map(b=>b.toString(16).padStart(2,"0")).join("");
const userId=async n=>hex(await crypto.subtle.digest("SHA-256",TE.encode("tender-scanner:"+n.trim().toLowerCase())));
const getJSON=u=>fetch(u,{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("HTTP "+r.status);return r.json()});
async function deriveKek(pw,u){
  const base=await crypto.subtle.importKey("raw",TE.encode(pw),"PBKDF2",false,["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({name:"PBKDF2",hash:"SHA-256",salt:b64d(u.salt),iterations:u.iterations},base,256));
}
async function unwrapKey(kek,u){
  const k=await crypto.subtle.importKey("raw",kek,"AES-GCM",false,["decrypt"]);
  const raw=await crypto.subtle.decrypt({name:"AES-GCM",iv:b64d(u.iv),additionalData:TE.encode("tender-scanner-key")},k,b64d(u.wrappedKey));
  return crypto.subtle.importKey("raw",raw,"AES-GCM",false,["decrypt"]);
}
async function openData(dk){
  const buf=new Uint8Array(await (await fetch("data/tenders.enc",{cache:"no-store"})).arrayBuffer());
  if(String.fromCharCode(...buf.slice(0,4))!=="TSE1")throw new Error("bad file");
  const gz=await crypto.subtle.decrypt({name:"AES-GCM",iv:buf.slice(4,16),additionalData:buf.slice(0,4)},dk,buf.slice(16));
  const txt=await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
  return JSON.parse(txt);
}
function saved(){try{return JSON.parse(localStorage.getItem(SKEY)||sessionStorage.getItem(SKEY)||"null")}catch(e){return null}}
function forget(){localStorage.removeItem(SKEY);sessionStorage.removeItem(SKEY)}
function showLogin(msg){
  document.body.classList.remove("authed");document.body.classList.add("locked");
  $("#lerr").textContent=msg||"";$("#lerr").hidden=!msg;
  const b=$("#lbtn");b.disabled=false;b.textContent="Log in";
  setTimeout(()=>($("#lu").value?$("#lp"):$("#lu")).focus(),50);
}
async function start(dk,name){
  const d=await openData(dk);
  META=d.meta||{};ALL=d.tenders||[];
  document.body.classList.remove("locked");document.body.classList.add("authed");
  $("#who").textContent=name;init();
}
async function resume(){
  const s=saved();
  if(!s)return showLogin();
  try{
    const users=(await getJSON("data/users.json")).users||{};
    const u=users[s.id];
    if(!u)throw new Error("gone");
    const dk=await unwrapKey(b64d(s.kek),u);
    await start(dk,s.name);
  }catch(e){forget();showLogin("Your login has changed. Please log in again.")}
}
function logout(){forget();location.reload()}
async function login(ev){
  ev.preventDefault();
  const name=$("#lu").value.trim().toLowerCase(),pw=$("#lp").value,rem=$("#lr").checked;
  if(!name||!pw)return showLogin("Enter your username and password.");
  const b=$("#lbtn");b.disabled=true;b.textContent="Checking…";$("#lerr").hidden=true;
  let users;
  try{users=(await getJSON("data/users.json")).users||{}}catch(e){return showLogin("Could not reach the dashboard. Check your internet and try again.")}
  const id=await userId(name),u=users[id];
  let dk=null,kek=null;
  if(u){try{kek=await deriveKek(pw,u);dk=await unwrapKey(kek,u)}catch(e){dk=null}}
  else{await new Promise(r=>setTimeout(r,600))}
  if(!dk){$("#lp").value="";return showLogin("Wrong username or password. Please try again.")}
  const rec=JSON.stringify({id,name,kek:b64e(kek)});
  forget();(rem?localStorage:sessionStorage).setItem(SKEY,rec);
  try{await start(dk,name)}catch(e){showLogin("Logged in, but the tender data could not be opened. Try again in a few minutes.")}
}
$("#lform").addEventListener("submit",login);
$("#logout").addEventListener("click",logout);
$("#lshow").addEventListener("click",()=>{const p=$("#lp");p.type=p.type==="password"?"text":"password";$("#lshow").textContent=p.type==="password"?"Show":"Hide"});
if(!(window.crypto&&crypto.subtle&&window.DecompressionStream)){showLogin("This browser is too old. Please update Chrome / Safari and open the link again.");$("#lbtn").disabled=true}
else{
  getJSON("data/meta.json").then(m=>{if(m.updated)$("#lupd").textContent="Last scan: "+fmtUpd(m.updated)}).catch(()=>{});
  resume();
}
})();
