export const TRANSFORMS = [
  {id:'objective',label:'Scoring objective',detail:'Change which value / utility signal is optimized.'},
  {id:'budget',label:'Sketch size & budget',detail:'Vary sketch dimensions under a fixed memory budget.'},
  {id:'tradeoff',label:'Memory / latency tradeoff',detail:'Compare retention quality against runtime and memory.'}
];

export function validateCase(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !Array.isArray(value.a) || !Array.isArray(value.m) || !value.current || typeof value.current !== 'object') throw Error('Case must contain current, a[], and m[].');
  const safeUrl = (u) => {
    if (typeof u !== 'string' || u.length > 2048) return false;
    try { const x=new URL(u); return x.protocol==='https:' && !!x.hostname && !x.username && !x.password; } catch { return false; }
  };
  const safeText = (v,n) => typeof v === 'string' && v.trim().length > 0 && v.length <= n;
  const safeId = (v) => safeText(v,64) && /^[A-Za-z0-9_-]{1,64}$/.test(v);
  if (!safeText(value.current.name,180) || !safeUrl(value.current.url)) throw Error('Current paper needs a name and safe HTTPS source URL.');
  for (const [group,items] of [['A',value.a],['M',value.m]]) {
    if (!items.length || items.length > 40) throw Error(group+' must contain 1–40 entries.');
    const seen=new Set();
    for (const item of items) {
      if (!item || !safeId(item.id) || seen.has(item.id) || !safeText(item.name,180) || !safeText(item.summary,1200) || !safeUrl(item.url)) throw Error('Invalid or duplicate '+group+' entry; each needs a safe ID, name, summary and HTTPS source.');
      seen.add(item.id);
    }
  }
  return value;
}

export function generateCandidates(data, {depth=1, aIds=data.a.map(x=>x.id), mIds=data.m.map(x=>x.id), limit=500}={}) {
  const aa=data.a.filter(x=>aIds.includes(x.id)), mm=data.m.filter(x=>mIds.includes(x.id));
  const base=[];
  for (const a of aa) for (const m of mm) {
    const blocked=a.id==='streamingllm';
    base.push({a,m,blocked,path:[],id:`${a.id}__${m.id}`,status:'UNTESTED'});
  }
  let items=base;
  for(let level=2;level<=Math.min(3,depth);level++) {
    items=items.flatMap(parent=>TRANSFORMS.map(t=>({a:parent.a,m:parent.m,blocked:parent.blocked,path:[...parent.path,t],parentId:parent.id,id:`${parent.id}__${t.id}`,status:'UNTESTED'})));
  }
  return items.slice(0,Math.max(0,limit));
}

export function compatibility(candidate) { return candidate.blocked ? {label:'Blocked by fit gate',score:0,reason:'StreamingLLM optimizes streaming-window and attention-sink retention, not the same eviction objective as CurDKV. It is not a direct plug-in for a leverage-score estimator. First reformulate the problem and demonstrate compatible selection units.'} : {label:'Unreviewed structural fit',score:Math.min(90,58+(candidate.a.id==='attn-family'?12:0)+(candidate.m.id==='gaussian'?14:0)+(candidate.path.length?4:0)),reason:'The components can be described in a shared KV selection design. This heuristic is not evidence of correctness or performance.'}; }
