const REPO='uniquegkquize-coder/globaltech-daily';
const CATS=['technology','government-schemes','sarkari-naukri','private-vacancy','movies-entertainment','world-news','business','sports','automobiles','health-science','gaming','environment','travel','education','lifestyle'];
const reply=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}});
function decode64(s){return Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0));}
async function verifiedEmail(request,env){
 const token=request.headers.get('Cf-Access-Jwt-Assertion');
 const team=(env.CF_ACCESS_TEAM_DOMAIN||'').replace(/^https?:\/\//,'').replace(/\/$/,'');
 if(!token||!team||!env.CF_ACCESS_AUD)return null;
 const parts=token.split('.');if(parts.length!==3)return null;
 try{
  const header=JSON.parse(new TextDecoder().decode(decode64(parts[0])));
  const claims=JSON.parse(new TextDecoder().decode(decode64(parts[1])));
  if(header.alg!=='RS256'||!header.kid||claims.iss!==`https://${team}`||!Array.isArray(claims.aud)||!claims.aud.includes(env.CF_ACCESS_AUD)||claims.exp<=Date.now()/1000||claims.nbf>Date.now()/1000)return null;
  const jwks=await fetch(`https://${team}/cdn-cgi/access/certs`,{cf:{cacheTtl:300,cacheEverything:true}}).then(r=>r.json());
  const key=jwks.keys.find(k=>k.kid===header.kid&&k.kty==='RSA');
  if(!key)return null;
  const cryptoKey=await crypto.subtle.importKey('jwk',key,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  const valid=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',cryptoKey,decode64(parts[2]),new TextEncoder().encode(parts[0]+'.'+parts[1]));
  return valid?String(claims.email||'').toLowerCase():null;
 }catch{return null;}
}
export async function onRequest({request,env}){
 const email=await verifiedEmail(request,env);
 if(!email||email!==String(env.ADMIN_EMAIL||'').toLowerCase())return reply({error:'Access denied. Configure Cloudflare Access and the approved admin email.'},403);
 if(request.method==='GET')return reply({ok:true,email,categories:CATS});
 if(request.method!=='POST')return reply({error:'Method not allowed'},405);
 if(!env.GITHUB_WRITE_TOKEN)return reply({error:'GitHub write token not configured'},503);
 if(Number(request.headers.get('content-length')||0)>60000)return reply({error:'Payload too large'},413);
 let input;try{input=await request.json()}catch{return reply({error:'Invalid JSON'},400)}
 const title=String(input.title||'').trim(),hiTitle=String(input.hi_title||'').trim();
 const body=String(input.body||'').trim(),hiBody=String(input.hi_body||'').trim();
 const source=String(input.source||'').trim(),category=String(input.category||'');
 if(title.length<15||title.length>180||body.length<150||body.length>25000||hiTitle.length<5||hiTitle.length>180||hiBody.length<100||hiBody.length>25000||!CATS.includes(category))return reply({error:'Fill valid English/Hindi titles, article bodies and category.'},400);
 let u;try{u=new URL(source)}catch{return reply({error:'Valid source URL required'},400)}
 if(u.protocol!=='https:'||!u.hostname.includes('.'))return reply({error:'HTTPS source URL required'},400);
 const id=crypto.randomUUID().replace(/-/g,'').slice(0,12);
 const now=new Date().toISOString();
 const post={id,en_title:title,hi_title:hiTitle,en_body:body,hi_body:hiBody,category,source:u.href,source_title:title,date:now,author:'GlobeWire Daily Editorial'};
 const bytes=new TextEncoder().encode(JSON.stringify(post,null,2)+'\n');
 let binary='';for(const b of bytes)binary+=String.fromCharCode(b);
 const api=`https://api.github.com/repos/${REPO}/contents/content/posts/${id}.json`;
 const result=await fetch(api,{method:'PUT',headers:{'authorization':`Bearer ${env.GITHUB_WRITE_TOKEN}`,'accept':'application/vnd.github+json','content-type':'application/json','x-github-api-version':'2022-11-28','user-agent':'GlobeWireDailyAdmin'},body:JSON.stringify({message:`Publish manual editorial article ${id}`,content:btoa(binary),branch:'main'})});
 if(!result.ok)return reply({error:'GitHub publish failed',status:result.status},502);
 return reply({ok:true,id,message:'Saved to repository. Site rebuild/deployment must complete before it appears.'},201);
}
