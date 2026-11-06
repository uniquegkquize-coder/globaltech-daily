/**
 * Preview-only Cloudflare R2 article delivery.
 * No production route is configured. Bind ARTICLE_HTML_BUCKET to a private R2 bucket.
 * Upload keys must match: en/news/<category>/<slug>/index.html.
 */
const ARTICLE = /^\/(en|hi)\/news\/([a-z0-9-]{1,80})\/([a-z0-9-]{1,180})\/$/;
const HTML_HEADERS = {
  "content-type": "text/html; charset=utf-8",
  "x-content-type-options": "nosniff",
  "cache-control": "public, max-age=60, s-maxage=300",
};
export default {
  async fetch(request, env, ctx) {
    if (request.method !== "GET" && request.method !== "HEAD")
      return new Response("Method Not Allowed", {status:405, headers:{allow:"GET, HEAD"}});
    const url = new URL(request.url);
    const match = url.pathname.match(ARTICLE);
    if (!match) return new Response("Not Found", {status:404});
    if (!env.ARTICLE_HTML_BUCKET) return new Response("Preview storage not configured", {status:503});
    const key = url.pathname.slice(1) + "index.html";
    const cacheKey = new Request("https://article-preview-cache.invalid/" + key);
    const cache = caches.default;
    let cached = await cache.match(cacheKey);
    if (!cached) {
      let object;
      try { object = await env.ARTICLE_HTML_BUCKET.get(key); }
      catch { return new Response("Storage temporarily unavailable", {status:503}); }
      if (!object) return new Response("Not Found", {status:404});
      const html = await object.text();
      if (!/<html[\s>]/i.test(html) || !/<\/html\s*>/i.test(html))
        return new Response("Invalid HTML", {status:502});
      cached = new Response(html, {status:200, headers:HTML_HEADERS});
      ctx.waitUntil(cache.put(cacheKey, cached.clone()));
    }
    return request.method === "HEAD"
      ? new Response(null, {status:cached.status, headers:cached.headers})
      : cached;
  }
};
