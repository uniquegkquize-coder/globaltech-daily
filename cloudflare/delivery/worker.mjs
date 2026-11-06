// Full HTML delivery. No global Pages middleware, HTML rewriting, source fetches,
// cron, writes, or recursive fetch(request). Only three production route prefixes.
const SCOPED = /^(?:\/(?:en|hi)(?:\/|$)|\/images\/)/;
const encoder = new TextEncoder();
async function sha(text) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(text)))].map(x => x.toString(16).padStart(2, '0')).join('');
}
const headers = {'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'strict-origin-when-cross-origin'};
function error(status, text) { return new Response(text, {status, headers:{...headers,'Cache-Control':'no-store'}}); }
async function jsonObject(bucket, key, cache, ctx) {
  const request = new Request('https://r2-manifest.invalid/'+key);
  const found = await cache.match(request);
  if (found) return found.json();
  const object = await bucket.get(key);
  if (!object) throw new Error('Missing release metadata');
  const data = await object.text();
  const response = new Response(data, {headers:{'Content-Type':'application/json','Cache-Control':'public, max-age=31536000, immutable'}});
  ctx.waitUntil(cache.put(request, response.clone()));
  return JSON.parse(data);
}
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (!['GET','HEAD'].includes(request.method)) return new Response('Method Not Allowed',{status:405,headers:{Allow:'GET, HEAD'}});
    if (!SCOPED.test(url.pathname)) {
      // Preview assets have an explicit Pages origin. Production routes never reach here.
      if (url.hostname.endsWith('.workers.dev') && env.ASSET_ORIGIN) {
        const origin = new URL(env.ASSET_ORIGIN);
        if (!origin.hostname.endsWith('.pages.dev') || origin.protocol !== 'https:') return error(503,'Invalid asset origin');
        return fetch(new URL(url.pathname+url.search, origin), {method:request.method,redirect:'manual'});
      }
      return error(404,'Not Found');
    }
    if (/%(?:2f|5c|00)/i.test(url.pathname) || url.pathname.includes('\\') || url.pathname.length > 1024) return error(404,'Not Found');
    let path;
    try { path = decodeURIComponent(url.pathname); } catch { return error(400,'Invalid path'); }
    if (path.split('/').some(p=>p==='..'||p==='.'||p.startsWith('.'))) return error(404,'Not Found');
    const releaseId = env.RELEASE_ID;
    if (!/^[a-f0-9]{64}$/.test(releaseId || '')) return error(503,'Release unavailable');
    // index.html and missing trailing slash resolve in a single hop to the exact public URL.
    let normalized = path;
    if (!path.startsWith('/images/')) {
      normalized = normalized.replace(/index\.html$/, '');
      if (!normalized.endsWith('/')) normalized += '/';
    }
    const cache = caches.default;
    const preview = url.hostname !== 'globewiredaily.org';
    const key = new Request('https://delivery-cache.invalid/'+releaseId+normalized);
    try {
      let response = await cache.match(key);
      if (!response) {
        const release = await jsonObject(env.MEDIA, 'releases/'+releaseId+'.json',cache,ctx);
        const shardId = (await sha(normalized)).slice(0,2);
        const shardKey = release.shards[shardId];
        if (!shardKey) return error(404,'Not Found');
        const shard = await jsonObject(env.MEDIA,shardKey,cache,ctx);
        const row = shard[normalized];
        if (!row) return error(404,'Not Found');
        if (row.redirect || normalized !== path) {
          const target = row.redirect || normalized;
          // Query-string image versions and attribution parameters survive redirects.
          return new Response(null,{status:row.status || 301, headers:{...headers,Location:target+url.search,'Cache-Control':'public, max-age=300',...(preview?{'X-Robots-Tag':'noindex'}:{})}});
        }
        const object = await env.MEDIA.get(row.key);
        if (!object) return error(503,'Content temporarily unavailable');
        if (object.size !== row.bytes || object.customMetadata?.sha256 !== row.sha256) return error(503,'Content verification failed');
        response = new Response(object.body,{headers:{...headers,'Content-Type':row.type,'Content-Length':String(row.bytes),ETag:'"'+row.sha256+'"',
          'Cache-Control':row.type.startsWith('image/')?'public, max-age=86400':'public, max-age=60, s-maxage=300, no-transform'}});
        ctx.waitUntil(cache.put(key,response.clone()));
      }
      if (normalized !== path) return new Response(null,{status:301,headers:{Location:normalized+url.search,...headers}});
      const result = new Headers(response.headers);
      if (preview) result.set('X-Robots-Tag','noindex');
      if (request.headers.get('If-None-Match') === result.get('ETag')) return new Response(null,{status:304,headers:result});
      return new Response(request.method === 'HEAD' ? null : response.body,{status:response.status,headers:result});
    } catch {
      // No fallback to old pages or cached wrong releases; monitoring receives an actionable 503.
      return error(503,'Content temporarily unavailable');
    }
  }
};
