addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});document.addEventListener('click',async function(ev){const share=ev.target.closest('.native-share');if(share){const data={title:share.dataset.shareTitle,url:share.dataset.shareUrl};if(navigator.share){try{await navigator.share(data)}catch(err){if(err.name!=='AbortError')location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}else{location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}const copy=ev.target.closest('.copy-share');if(copy){try{await navigator.clipboard.writeText(copy.dataset.shareUrl);const old=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>copy.textContent=old,1800)}catch(err){prompt('Copy link:',copy.dataset.shareUrl)}}});document.querySelectorAll('[data-news-search]').forEach(input=>{input.addEventListener('input',()=>{let q=input.value.trim().toLocaleLowerCase();let scope=input.closest('[data-news-hub]');let rows=scope.querySelectorAll('[data-search-text]');let count=0;rows.forEach(row=>{let match=row.dataset.searchText.toLocaleLowerCase().includes(q);row.hidden=!match;if(match)count++;});let status=scope.querySelector('[data-search-status]');if(status)status.textContent=scope.dataset.searchLanguage==='hi'?`${count} खबरें मिलीं`:`${count} matching updates`;});});document.querySelectorAll('[data-archive-filter]').forEach(root=>{let input=root.querySelector('input'),select=root.querySelector('select'),status=root.querySelector('[role="status"]');function run(){let q=input.value.toLocaleLowerCase(),year=select.value,n=0;root.querySelectorAll('[data-archive-row]').forEach(row=>{let show=row.dataset.searchText.toLocaleLowerCase().includes(q)&&(!year||row.dataset.year===year);row.hidden=!show;if(show)n++;});status.textContent=root.dataset.lang==='hi'?`${n} रिकॉर्ड मिले`:`${n} records found`;}input.addEventListener('input',run);select.addEventListener('change',run);});
document.querySelectorAll('[data-directory]').forEach(root=>{
 const search=root.querySelector('[data-search]'),country=root.querySelector('[data-country]'),region=root.querySelector('[data-region]'),city=root.querySelector('[data-city]'),count=root.querySelector('[data-count]');
 const cards=[...root.querySelectorAll('[data-item]')];
 function update(){
  const q=search.value.trim().toLocaleLowerCase();
  let shown=0;
  cards.forEach(card=>{
   const match=card.dataset.search.includes(q)&&(!country.value||card.dataset.country===country.value)&&(!region.value||card.dataset.region===region.value)&&(!city.value||card.dataset.city===city.value);
   card.hidden=!match;if(match)shown++;
  });
  count.textContent=shown+' results';
 }
 function options(select,field){
  const previous=select.value;
  const values=[...new Set(cards.filter(card=>(!country.value||card.dataset.country===country.value)&&(field==='city'?(!region.value||card.dataset.region===region.value):true)).map(card=>card.dataset[field]).filter(Boolean))].sort();
  select.innerHTML='<option value="">All '+field+'s</option>'+values.map(v=>'<option value="'+v.replaceAll('&','&amp;').replaceAll('"','&quot;')+'">'+v.replaceAll('&','&amp;').replaceAll('<','&lt;')+'</option>').join('');
  select.value=values.includes(previous)?previous:'';
 }
 if(country){country.addEventListener('change',()=>{options(region,'region');options(city,'city');update()});region.addEventListener('change',()=>{options(city,'city');update()});city.addEventListener('change',update)}
 search.addEventListener('input',update);update();
});
