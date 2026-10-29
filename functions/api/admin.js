const REPO='uniquegkquize-coder/globaltech-daily';
const CATS=['technology','government-schemes','sarkari-naukri','private-vacancy','movies-entertainment','world-news','business','sports','automobiles','health-science','gaming','environment','travel','education','lifestyle'];
const reply=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}});
const enc=new TextEncoder();
const base64=b=>btoa(String.fromCharCode(...b)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function from64(s){return Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0));}
async function hmac(message,secret){
 const key=await crypto.subtle.importKey('raw',enc.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 return base64(new Uint8Array(await crypto.subtle.sign('HMAC',key,enc.encode(message))));
}
async function authorized(request,env){
 if(!env.ADMIN_SESSION_SECRET||!env.ADMIN_EMAIL)return false;
 const match=(request.headers.get('cookie')||'').match(/(?:^|; )gwd_admin=([^;]+)/);
 if(!match)return false;
 const [payload,sig]=match[1].split('.');
 if(!payload||!sig||sig!==await hmac(payload,env.ADMIN_SESSION_SECRET))return false;
 try{const session=JSON.parse(new TextDecoder().decode(from64(payload)));return session.email===env.ADMIN_EMAIL.toLowerCase()&&session.exp>Date.now()}catch{return false}
}
const cookie=(value,maxAge)=>'gwd_admin='+value+'; HttpOnly; Secure; SameSite=Strict; Path=/api/admin; Max-Age='+maxAge;
async function login(request,env){
 if(!env.ADMIN_EMAIL||!env.ADMIN_PASSWORD||!env.ADMIN_SESSION_SECRET)return reply({error:'Admin credentials are not configured on the server.'},503);
 let data;try{data=await request.json()}catch{return reply({error:'Invalid request'},400)}
 const email=String(data.email||'').trim().toLowerCase(),password=String(data.password||'');
 if(email!==env.ADMIN_EMAIL.toLowerCase()||password!==env.ADMIN_PASSWORD)return reply({error:'Invalid email or password'},401);
 const payload=base64(enc.encode(JSON.stringify({email,exp:Date.now()+8*3600000})));
 const sig=await hmac(payload,env.ADMIN_SESSION_SECRET);
 const response=reply({ok:true,email});
 response.headers.set('set-cookie',cookie(payload+'.'+sig,28800));
 return response;
}
export async function onRequest({request,env}){
 if(request.method==='POST'&&new URL(request.url).searchParams.get('action')==='login')return login(request,env);
 if(request.method==='POST'&&new URL(request.url).searchParams.get('action')==='logout'){
  const response=reply({ok:true});response.headers.set('set-cookie',cookie('',0));return response;
 }
 if(!await authorized(request,env))return reply({error:'Not signed in'},401);
 if(request.method==='GET')return reply({ok:true,email:env.ADMIN_EMAIL,categories:CATS});
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
