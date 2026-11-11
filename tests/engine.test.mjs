import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import {generateCandidates,validateCase} from '../engine.mjs';
const data=JSON.parse(await readFile(new URL('../data/curdkv.json',import.meta.url),'utf8'));
test('depth yields 16, 48, and 144 pairings/branches',()=>{assert.equal(generateCandidates(data,{depth:1}).length,16);assert.equal(generateCandidates(data,{depth:2}).length,48);assert.equal(generateCandidates(data,{depth:3}).length,144);});
test('candidate ids are unique at each depth',()=>{for(const depth of [1,2,3]){const xs=generateCandidates(data,{depth});assert.equal(new Set(xs.map(x=>x.id)).size,xs.length);}});
test('every generated candidate is explicitly untested',()=>{for(const depth of [1,2,3])assert.ok(generateCandidates(data,{depth}).every(x=>x.status==='UNTESTED'));});
test('incompatible StreamingLLM and SVD is flagged',()=>{const [x]=generateCandidates(data,{aIds:['streamingllm'],mIds:['svd']});assert.equal(x.blocked,true);});
test('validation rejects malformed case and unsafe URL schemes',()=>{assert.throws(()=>validateCase({}));const bad=structuredClone(data);bad.a[0].url='javascript:alert(1)';assert.throws(()=>validateCase(bad));});

test('streaming objective is flagged against all mechanisms',()=>{for(const x of generateCandidates(data,{aIds:['streamingllm']}))assert.equal(x.blocked,true);});
test('import requires HTTPS, distinct IDs and safe current source',()=>{const a=structuredClone(data);a.a[0].url='http://example.org/paper';assert.throws(()=>validateCase(a));const b=structuredClone(data);b.a[1].id=b.a[0].id;assert.throws(()=>validateCase(b));const c=structuredClone(data);c.current.url='javascript:alert(1)';assert.throws(()=>validateCase(c));});
