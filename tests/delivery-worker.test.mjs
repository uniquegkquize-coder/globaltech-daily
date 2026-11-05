import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import worker from '../cloudflare/delivery/worker.mjs';
globalThis.crypto ??= webcrypto;
const sha = async x => [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(x)))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function fixture() {
  const store = new Map(), cache = new Map(), tasks=[];
  globalThis.caches = {default:{match:async req=>cache.get(req.url)?.clone(),put:async(req,res)=>cache.set(req.url,res.clone())}};
  const html='<html lang="en"><head><link rel="canonical" href="https://globewiredaily.org/en/news/science/test/"><link rel="alternate" hreflang="hi" href="https://globewiredaily.org/hi/news/science/test/"></head><body>News</body></html>';
  const hash=await sha(html), release='a'.repeat(64);
  const routes={'/en/':{key:'html',sha256:hash,bytes:Buffer.byteLength(html),type:'text/html; charset=utf-8'},
    '/en/news/science/test/':{key:'html',sha256:hash,bytes:Buffer.byteLength(html),type:'text/html; charset=utf-8'},
    '/hi/news/science/test/':{key:'hindi',sha256:await sha('हिंदी'),bytes:Buffer.byteLength('हिंदी'),type:'text/html; charset=utf-8'},
    '/images/a.jpg':{key:'image',sha256:await sha('image'),bytes:5,type:'image/jpeg'},
    '/en/news/old/':{redirect:'/en/news/science/test/',status:301}};
  const releaseObj={shards:{}};
  for(const [path,row] of Object.entries(routes)) {
    const shard=(await sha(path)).slice(0,2),key='shard/'+shard;
    releaseObj.shards[shard]=key;
    if (!store.has(key)) store.set(key,{});
    store.get(key)[path]=row;
  }
  store.set('releases/'+release+'.json',releaseObj);
  store.set('html',html);store.set('hindi','हिंदी');store.set('image','image');
  let reads=0;
  const env={RELEASE_ID:release,MEDIA:{get:async key=>{
    reads++;const value=store.get(key);if(value===undefined)return null;
    const text=typeof value==='string'?value:JSON.stringify(value);
    return {text:async()=>text,body:text,size:Buffer.byteLength(text),customMetadata:{sha256:await sha(text)}};
  }}};
  const ctx={waitUntil:p=>tasks.push(p)};
  const request=async(path,options={},host='globewiredaily.org')=>{
    const r=await worker.fetch(new Request('https://'+host+path,options),env,ctx);await Promise.all(tasks);return r;
  };
  return {request,env,store,get reads(){return reads},html};
}
test('canonical HTML and Hindi bytes preserve SEO and language',async()=>{
  const f=await fixture();const r=await f.request('/en/news/science/test/');assert.equal(r.status,200);assert.equal(await r.text(),f.html);
  const h=await f.request('/hi/news/science/test/');assert.equal(await h.text(),'हिंदी');assert.ok(!r.headers.has('X-Robots-Tag'));
});
test('legacy URLs emit 301 with query preserved, no redirect stub',async()=>{
  const f=await fixture();const r=await f.request('/en/news/old/?utm_source=x');assert.equal(r.status,301);assert.equal(r.headers.get('Location'),'/en/news/science/test/?utm_source=x');
});
test('missing-slash and index.html canonicalize even when cache warm',async()=>{
  const f=await fixture();await f.request('/en/news/science/test/');
  for(const path of ['/en/news/science/test','/en/news/science/test/index.html']) {
    const r=await f.request(path);assert.equal(r.status,301);assert.equal(r.headers.get('Location'),'/en/news/science/test/');
  }
});
test('legacy images retain path, bytes, MIME and version query compatibility',async()=>{
  const f=await fixture();const r=await f.request('/images/a.jpg?v=abc');assert.equal(r.status,200);assert.equal(await r.text(),'image');assert.equal(r.headers.get('Content-Type'),'image/jpeg');
});
test('HEAD and conditional GET avoid response body',async()=>{
  const f=await fixture();const r=await f.request('/en/',{method:'HEAD'});assert.equal(r.status,200);assert.equal(await r.text(),'');
  assert.equal((await f.request('/en/',{headers:{'If-None-Match':r.headers.get('ETag')}})).status,304);
});
test('cache hits avoid R2 reads and release change selects rollback snapshot',async()=>{
  const f=await fixture();await f.request('/en/');const reads=f.reads;await f.request('/en/');assert.equal(f.reads,reads);
  f.env.RELEASE_ID='b'.repeat(64);assert.equal((await f.request('/en/')).status,503);
  f.env.RELEASE_ID='a'.repeat(64);assert.equal((await f.request('/en/')).status,200);
});
test('scope, unknown paths and methods fail closed',async()=>{
  const f=await fixture();for(const path of ['/style.css','/admin/','/en/missing/','/images/missing.jpg','/en/%2fsecret/'])assert.equal((await f.request(path)).status,404);
  assert.equal((await f.request('/en/',{method:'POST'})).status,405);
});
test('missing content gives 503 and is not cached as a false article',async()=>{
  const f=await fixture();f.store.delete('html');assert.equal((await f.request('/en/')).status,503);f.store.set('html',f.html);assert.equal((await f.request('/en/')).status,200);
});
test('R2 exceptions give bounded 503 without origin fallback',async()=>{
  const f=await fixture();f.env.MEDIA.get=async()=>{throw Error('unavailable')};assert.equal((await f.request('/en/')).status,503);
});
test('preview carries noindex without changing canonical HTML',async()=>{
  const f=await fixture();const r=await f.request('/en/news/science/test/',{},'preview.workers.dev');assert.equal(r.headers.get('X-Robots-Tag'),'noindex');assert.equal(await r.text(),f.html);
});
