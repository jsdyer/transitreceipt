import {matchRows,statistics,csv,valueLabel,groupReceipts} from './model.mjs';
import config from './config.mjs';
const $=id=>document.getElementById(id);
const text=(id,value)=>{$(id).textContent=value;};
const el=(tag,value,cls)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=value;if(cls)node.className=cls;return node;};
const fmt=(value,digits=2)=>value===null?'—':new Intl.NumberFormat('en-CA',{maximumFractionDigits:digits}).format(value);
const when=value=>value ? new Date(value).toISOString().replace('T',' ').slice(0,16)+' UTC':'Not supplied';
let data,activeRows=[];
document.documentElement.style.setProperty('--accent',config.accent);
document.documentElement.style.setProperty('--accent-light',config.tint);
for(const [id,value] of Object.entries(config.text))if($(id))text(id,value);
for(const p of config.method)$('explanation').append(el('p',p));
for(const source of config.sources){const a=el('a',source.label);a.href=source.url;const li=el('li');li.append(a);$('sources').append(li);}
function link(label,href){const a=el('a',label);a.href=href;return a;}
function options(node,values){node.replaceChildren();for(const [value,label] of values){const o=el('option',label);o.value=value;node.append(o);}}
function receipts(){return data.receipts.filter(r=>r.entity===$('entity').value);}
function setReceipts(){const available=receipts();options($('receipt'),available.map(r=>[r.id,`${r.items[0]?.target_time?.slice(0,10)||r.items[0]?.target?.slice(0,10)} · ${r.provenance==='published_archive'?'issued':'saved'} ${when(r.provenance==='published_archive'?r.issued_at:r.captured_at)} · ${r.items.length} points${r.provenance==='published_archive'?' · archived issue':''}`]));const matched=available.find(r=>matchRows(r,data.observations,config.kind).some(p=>p.observed!==null));if(matched)$('receipt').value=matched.id;render();}
function chart(rows){
  const holder=$('chart');holder.replaceChildren();
  if(!rows.length){holder.append(el('p','No points match this view.'));return;}
  const points=rows.slice(0,120),transit=config.kind==='transit';
  const values=points.flatMap(r=>[r.value,...(r.observed===null?[]:[r.observed])]);
  let low=Math.min(...values),high=Math.max(...values);const pad=(high-low)*.13||1;low-=pad;high+=pad;
  const NS='http://www.w3.org/2000/svg';const svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 1000 300');svg.setAttribute('aria-hidden','true');
  function s(tag,attrs,txt){const n=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(txt)n.textContent=txt;svg.append(n);return n;}
  const x=i=>65+(points.length===1?440:i/(points.length-1)*900),y=v=>252-(v-low)/(high-low)*220;
  for(let i=0;i<5;i++){const v=low+(high-low)*i/4,yp=y(v);s('line',{x1:65,x2:965,y1:yp,y2:yp,stroke:'#dce5e9'});s('text',{x:54,y:yp+4,'text-anchor':'end'},transit?new Date(v*1000).toISOString().slice(11,16):fmt(v,config.kind==='tide'?2:0));}
  s('polyline',{points:points.map((r,i)=>`${x(i)},${y(r.value)}`).join(' '),fill:'none',stroke:config.accent,'stroke-width':2.5});
  // Observations remain isolated dots: do not draw lines across missing observations.
  points.forEach((r,i)=>{if(r.observed!==null){const n=s('circle',{cx:x(i),cy:y(r.observed),r:4,fill:'#c14e32'});const title=document.createElementNS(NS,'title');title.textContent=`${r.target_time||r.target}: ${valueLabel(r.observed,config.kind)}`;n.append(title);}});
  [...new Set([0,Math.floor(points.length/2),points.length-1])].forEach(i=>s('text',{x:x(i),y:281,'text-anchor':i===0?'start':i===points.length-1?'end':'middle'},new Date(points[i].target_time||points[i].target).toISOString().slice(5,16).replace('T',' ')+' UTC'));
  holder.append(svg);
}
function render(){
  const receipt=receipts().find(r=>r.id===$('receipt').value);
  const all=matchRows(receipt,data.observations,config.kind);const stats=statistics(all);
  activeRows=all.filter(r=>$('filter').value==='all'||($('filter').value==='matched'?r.observed!==null:r.observed===null));
  text('matched',`${stats.count} / ${stats.total}`);text('mae',stats.mae===null?'—':`${fmt(stats.mae)} ${config.unit}`);text('bias',stats.bias===null?'—':`${stats.bias>0?'+':''}${fmt(stats.bias)} ${config.unit}`);
  text('mae-help',stats.count?`${stats.count} matched points in this receipt`:'This receipt has no matched outcomes yet');
  $('export').disabled=!activeRows.length;
  $('receipt-meta').replaceChildren();
  if(receipt){$('receipt-meta').append(el('span',`Captured ${when(receipt.captured_at)}`),link('Saved receipt (.json.gz)','./'+receipt.file),link('Source',receipt.source_url));if(receipt.issued_at)$('receipt-meta').append(el('span',`Issued ${when(receipt.issued_at)}`));if(receipt.provenance==='published_archive')$('receipt-meta').append(el('strong','Published archive: retrieved after issue, not captured live.'));}
  chart(activeRows);
  text('chart-caption',config.chartCaption);
  $('rows').replaceChildren();
  for(const r of activeRows.slice(0,150)){
    const tr=el('tr');const target=el('td',when(r.target_time||r.target));if(r.label)target.append(el('small',r.label));tr.append(target);
    tr.append(el('td',valueLabel(r.value,config.kind)),el('td',valueLabel(r.observed,config.kind),r.observed===null?'pending':''));
    tr.append(el('td',r.error===null?'—':`${r.error>0?'+':''}${fmt(r.error)} ${config.unit}`,r.error===null?'pending':r.error>=0?'positive':'negative'));
    tr.append(el('td',config.kind==='transit'?`${fmt(r.lead*60,1)} min`:`${fmt(r.lead,1)} h`));const evidence=el('td');if(r.evidence)evidence.append(link(config.kind==='transit'?r.evidence.method||'Vehicle sighting':'Source receipt','./'+r.evidence.file));else evidence.textContent='Pending';tr.append(evidence);$('rows').append(tr);
  }
  $('empty').hidden=Boolean(activeRows.length);text('empty',all.length?'No points match this filter. Try All points.':'No future predictions were available at this location during the saved collection window.');
  text('table-note',`Showing ${Math.min(activeRows.length,150)} of ${activeRows.length} points. CSV includes every point in this view. Times are UTC. ${config.tableNote}`);
}
$('entity').addEventListener('change',setReceipts);$('receipt').addEventListener('change',render);$('filter').addEventListener('change',render);
$('export').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([csv(activeRows,config.kind)],{type:'text/csv;charset=utf-8'}));const a=link('Download',url);a.download=config.id+'-comparison.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
try{
 const response=await fetch('./data/index.json');if(!response.ok)throw new Error('Data unavailable');data=await response.json();
 text('archive-date',data.archive_began.slice(0,10));text('archive-count',`${data.archive_count.toLocaleString()} permanent source receipts`);
 text('status',`Latest collection: ${when(data.collection.checked_at)}`);
 text('coverage',data.collection.providers.map(p=>`${p.name}: ${p.status}`).join(' · '));
 const age=(Date.now()-Date.parse(data.collection.checked_at))/3600000;if(age>config.staleHours)text('status',`Collection is overdue. Last checked ${when(data.collection.checked_at)}. Showing saved data.`);
 options($('entity'),groupReceipts(data.receipts));setReceipts();
}catch(error){text('status','The saved data could not be loaded. Reload the page or use the repository archive.');$('export').disabled=true;console.error(error);}
