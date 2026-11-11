#!/usr/bin/env python3
"""Private, local benchmark preparation for research-problem search approaches."""
import argparse
import hashlib
import json
import math
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = 'http://127.0.0.1:18765/api/search'
PUBLIC_CODE_ROOT=Path(__file__).resolve().parents[1]
def private_output_path(path):
    target=Path(path).expanduser().resolve()
    if target==PUBLIC_CODE_ROOT or PUBLIC_CODE_ROOT in target.parents:
        raise ValueError('Benchmark outputs must be stored outside the public Research Explorer repository')
    return target

MAX_QUERY = 1000
MAX_TEXT = 12000
MAX_RESULTS = 100

def tokens(value):
    return re.findall(r"[\w]+", str(value or '').lower(), flags=re.UNICODE)

def safe_https(value):
    from urllib.parse import urlparse
    if not isinstance(value, str) or len(value) > 2048: return None
    u=urlparse(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password: return None
    return value

def records_from_payload(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        for key in ('results','papers','items','data'):
            if isinstance(payload.get(key),list): return payload[key]
    raise ValueError('Search API response has no result list')

def bm25(query, records, limit):
    q=list(dict.fromkeys(tokens(query)))
    docs=[tokens((r.get('title','')+' '+r.get('abstract',''))[:MAX_TEXT]) for r in records]
    n=len(docs); avg=sum(map(len,docs))/max(n,1); df={t:sum(t in d for d in docs) for t in q}; ranked=[]
    for rec,doc in zip(records,docs):
        score=0.0
        for term in q:
            tf=doc.count(term)
            if tf: score += math.log(1+(n-df[term]+.5)/(df[term]+.5))*tf*2.2/(tf+1.2*(.25+.75*len(doc)/max(avg,1)))
        if score: ranked.append((score,rec))
    ranked.sort(key=lambda x:(-x[0],str(x[1].get('title',''))))
    return ranked[:limit]

def cmd_retrieve(args):
    query=args.query[:MAX_QUERY]
    url=API+'?'+urllib.parse.urlencode({'q':query,'limit':min(args.limit,MAX_RESULTS)})
    req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'ResearchExplorer-local/1'})
    with urllib.request.urlopen(req,timeout=8) as response:
        if response.status != 200: raise RuntimeError('ConfHub API returned HTTP '+str(response.status))
        payload=json.loads(response.read(2_000_000).decode('utf-8'))
    source_records=records_from_payload(payload); clean=[]
    for r in source_records[:MAX_RESULTS]:
        if not isinstance(r,dict): continue
        link=safe_https(r.get('source_url') or r.get('paper_url') or r.get('url'))
        title=str(r.get('title',''))[:500]
        abstract=str(r.get('abstract',''))[:MAX_TEXT]
        if not link or not title: continue
        clean.append({'id':str(r.get('id',''))[:200],'title':title,'abstract':abstract,'venue':str(r.get('venue',''))[:200],'year':r.get('year'),'source_url':link,'provenance':{'service':'ConfHub loopback BM25 API','endpoint':API,'retrieval_query':query,'retrieved_unix':int(time.time())}})
    ranked=bm25(query,clean,min(args.limit,MAX_RESULTS))
    out={'schema':'research-taste-evidence/1','query':query,'retrieval':'local BM25 reranking of live ConfHub loopback results','records':[dict(r,lexical_score=round(s,6),matched_terms=[t for t in dict.fromkeys(tokens(query)) if t in tokens(r['title']+' '+r['abstract'])]) for s,r in ranked]}
    write_json(args.out,out)

def write_json(path, value):
    p=private_output_path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def prompt_text(arm, query, evidence, case, seed):
    base=('You are generating research directions, not claiming results. Return up to five distinct worthwhile similar RESEARCH PROBLEMS; each must be a distinct question, not a one-component swap or cosmetic edit. For each give problem statement, significance, source-linked abstract/metadata evidence and explicitly identified full-text passages to check later, novelty risk, compatibility/theory checks, rejection criteria, falsifiable experiment and controls, metrics, realistic compute estimate with assumptions, and reproducibility plan. Identify mathematical assumptions and mechanism checks needed. No external browsing or full-text tools are available during this controlled benchmark generation step; NEVER claim to have verified full texts, performed an exhaustive novelty search, or run experiments. Novelty remains UNVERIFIED. Mark unknowns honestly. Keep an ambitious, nontrivial research scope, quantify GPU-hours and memory assumptions, and reject trivial edits; do not fabricate citations, scores, or results. Do not reveal the prompting arm name. If fewer than five survive, explain why.\n')
    method=('BASELINE: brainstorm directly from the stated problem and evidence; do not use A/M decomposition.\n' if arm=='baseline' else 'STRUCTURED: separately inspect the A-side prior problem-family neighborhood and M-side borrowed-mechanism neighborhood, then propose distinct research problems that may connect them. Do not assume every combination is sound.\n')
    return base+method+f'Use benchmark seed {seed}.\nProblem: {query}\nA/M case context: {json.dumps(case,ensure_ascii=False)}\nEvidence papers (identical across arms): {json.dumps(evidence,ensure_ascii=False)}\n'

def cmd_prepare(args):
    ev=json.loads(Path(args.evidence).read_text(encoding='utf-8')); records=ev.get('records')
    if not isinstance(records,list) or not records: raise ValueError('Evidence must contain nonempty records')
    query=str(ev.get('query',''))[:MAX_QUERY]
    papers=[{k:r.get(k) for k in ('id','title','abstract','venue','year','source_url','provenance')} for r in records]
    if any(not safe_https(p.get('source_url')) for p in papers): raise ValueError('Every evidence record needs a safe HTTPS source')
    case={'case_status':'not_supplied','A_neighborhood':'derive from sources','M_neighborhood':'derive from sources'}
    case_path=getattr(args,'case',None)
    if case_path:
        cfile=Path(case_path)
        if cfile.stat().st_size>1_000_000: raise ValueError('Case JSON larger than 1 MB')
        raw_case=json.loads(cfile.read_text(encoding='utf-8'))
        if not isinstance(raw_case,dict) or not isinstance(raw_case.get('current'),dict): raise ValueError('Case requires current paper')
        current=raw_case['current']
        if not safe_https(current.get('url')): raise ValueError('Case current paper requires safe HTTPS URL')
        case={'case_status':'user_supplied_unreviewed',
              'current':{k:current.get(k) for k in ('name','fullTitle','url','claims')},
              'A_neighborhood':[{k:item.get(k) for k in ('id','name','summary','url','evidence')} for item in raw_case.get('a',[])[:20]],
              'M_neighborhood':[{k:item.get(k) for k in ('id','name','summary','url','evidence')} for item in raw_case.get('m',[])[:20]]}
        for group in ('A_neighborhood','M_neighborhood'):
            if any(not safe_https(item.get('url')) for item in case[group]): raise ValueError('Case alternatives require safe HTTPS URLs')
    manifest={'schema':'research-taste-blinded-benchmark/1','seed':args.seed,'query':query,'evidence':papers,'evidence_sha256':hashlib.sha256(json.dumps(papers,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'arms':['baseline','structured'],'controls':{'same_evidence':True,'same_model_required':True,'same_budget':True,'blind_outputs_for_judge':True,'no_quality_scores_before_independent_judging':True},'randomization':'Deterministic prompt preparation; arm identity should be withheld from independent grader.','case_status':case.get('case_status'),'case_sha256':hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    out=private_output_path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    write_json(out/'manifest.json',manifest)
    for arm in ('baseline','structured'):
        (out/(arm+'.prompt.txt')).write_text(prompt_text(arm,query,papers,case,args.seed),encoding='utf-8')

def claude_status(profile):
    env=os.environ.copy();env['CLAUDE_CONFIG_DIR']=str(Path(profile).expanduser().resolve())
    p=subprocess.run(['claude','auth','status','--json'],env=env,capture_output=True,text=True,timeout=20)
    if p.returncode: return False,'Claude CLI auth status failed'
    try: data=json.loads(p.stdout)
    except ValueError: return False,'Claude CLI returned unparseable auth status'
    return data.get('loggedIn') is True, 'loggedIn is not true'

def cmd_run(args):
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8')); arm=args.arm
    profile=Path(args.profile).expanduser()
    if args.dry_run:
        print(json.dumps({'dry_run':True,'arm':arm,'profile_path':str(profile),'model':args.model or 'profile default','tools':'empty','evidence_count':len(manifest.get('evidence',[]))}))
        return
    ok,reason=claude_status(profile)
    if not ok: print('BLOCKED: Claude Science profile unavailable: '+reason,file=sys.stderr); raise SystemExit(2)
    prompt=Path(Path(args.manifest).parent/(arm+'.prompt.txt')).read_text(encoding='utf-8')
    env=os.environ.copy();env['CLAUDE_CONFIG_DIR']=str(profile.resolve())
    command=['claude','--print','--strict-mcp-config','--tools','', '--no-session-persistence','--output-format','json']
    if args.model: command.extend(['--model',args.model])
    try: result=subprocess.run(command,input=prompt,text=True,capture_output=True,env=env,timeout=900)
    except subprocess.TimeoutExpired: raise RuntimeError('Claude CLI timed out at 900 seconds')
    if result.returncode: raise RuntimeError('Claude CLI failed; see stderr (not stored to public repo)')
    p=private_output_path(args.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(result.stdout,encoding='utf-8')

def cmd_score(args):
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    outputs={a:Path(getattr(args,a)).read_text(encoding='utf-8') for a in ('baseline','structured')}
    labels=['X','Y'];secrets.SystemRandom().shuffle(labels)
    assigned={'baseline':labels[0],'structured':labels[1]}
    blind=[{'blind_id':assigned[arm],'output':outputs[arm]} for arm in ('baseline','structured')]
    sheet={'schema':'research-taste-blind-grading/1','blind_outputs':blind,'ratings':None,'rubric':[{'dimension':d,'rating_0_to_4':None,'evidence_and_reasoning':''} for d in ('significance','originality after literature search','compatibility and theory','falsifiability','realistic compute','reproducibility')],'judge_instructions':'Independent judge: assign 0–4 only with written evidence and rationale; compare against identical evidence and model; do not infer quality from lexical matches. Preserve blind IDs while grading. Arm labels have been randomized. The coordinator mapping is saved in a separate private file alongside this sheet; never show that mapping to the independent judge.','mechanical_counts':{assigned[arm]:{'output_chars':len(outputs[arm]),'citation_urls':len(re.findall(r'https://[^\s)\]}>,]+',outputs[arm]))} for arm in ('baseline','structured')},'manifest_evidence_sha256':manifest.get('evidence_sha256'),'scores_fabricated':False}
    write_json(args.out,sheet)
    write_json(str(args.out)+'.mapping.private.json',{'blind_id_to_arm':{v:k for k,v in assigned.items()},'warning':'Keep this mapping private; do not provide it to the independent judge.'})

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('retrieve');r.add_argument('--query',required=True);r.add_argument('--out',required=True);r.add_argument('--limit',type=int,default=20);r.set_defaults(fn=cmd_retrieve)
    q=sub.add_parser('prepare');q.add_argument('--evidence',required=True);q.add_argument('--outdir',required=True);q.add_argument('--seed',type=int,default=42);q.add_argument('--case');q.set_defaults(fn=cmd_prepare)
    u=sub.add_parser('run');u.add_argument('--manifest',required=True);u.add_argument('--arm',choices=('baseline','structured'),required=True);u.add_argument('--profile',required=True);u.add_argument('--out',required=True);u.add_argument('--model');u.add_argument('--dry-run',action='store_true');u.set_defaults(fn=cmd_run)
    s=sub.add_parser('score');s.add_argument('--manifest',required=True);s.add_argument('--baseline',required=True);s.add_argument('--structured',required=True);s.add_argument('--out',required=True);s.set_defaults(fn=cmd_score)
    args=p.parse_args()
    if getattr(args,'limit',1)<1 or getattr(args,'limit',1)>MAX_RESULTS: p.error('limit must be 1..100')
    try: args.fn(args)
    except (OSError,ValueError,RuntimeError,urllib.error.URLError,TimeoutError) as e: print(str(e),file=sys.stderr);return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
