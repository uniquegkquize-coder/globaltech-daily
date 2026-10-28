// Cloudflare Pages middleware: redirect only the legacy pages.dev hostname.
// Preserve path and query string; leave the custom domain untouched.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname.toLowerCase() === 'globaltech-daily.pages.dev') {
    url.protocol = 'https:';
    url.hostname = 'globewiredaily.org';
    url.port = '';
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
