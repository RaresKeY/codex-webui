(config) => {
  // Only this repository-owned observer is executed; model text never becomes code.
  const visible = e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const sensitive = e => e.matches('input[type=password],input[type=hidden],input[type=file]') ||
    /password|token|secret|credit.card|security.code/i.test(e.getAttribute('name') || '');
  const filename = value => {
    try { return decodeURIComponent(new URL(value,location.href).pathname.split('/').pop()).replaceAll('_',' '); }
    catch { return 'Unlabelled image'; }
  };
  const label = e => {
    const values=[e.getAttribute('aria-label'),
      (e.getAttribute('aria-labelledby') || '').split(' ').map(id => document.getElementById(id)?.textContent || '').join(' '),
      e.labels ? [...e.labels].map(l=>l.innerText).join(' ') : '',
      e.innerText,e.getAttribute('title'),e.getAttribute('placeholder'),e.getAttribute('alt'),e.querySelector('img')?.alt];
    const meaningful=values.map(v=>(v || '').trim()).find(Boolean);
    return (meaningful || (e.tagName==='A' ? filename(e.href) : '')).slice(0,160);
  };
  let selector = 'a[href],button,input:not([type=hidden]),select,textarea,summary';
  if (config.include_custom) selector += ',[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=combobox],[tabindex="0"]';
  const content = document.querySelector('main,[role=main],#content') || document.body;
  const inContent = e => !!content?.contains(e);
  const inViewport = e => {
    const r=e.getBoundingClientRect();
    return r.bottom>0 && r.right>0 && r.top<innerHeight && r.left<innerWidth;
  };
  const all = [...document.querySelectorAll(selector)].filter(e => visible(e) && !sensitive(e));
  const mediaDestinations=new Set(all.filter(e=>e.tagName==='A' && e.querySelector('img')).map(e=>e.href));
  const preferredLabels=new Set(config.priority_labels || []);
  const priority = e => (preferredLabels.has(label(e))?16:0) + (inContent(e)?4:0) +
    (e.tagName==='A' && !e.querySelector('img') && e.innerText.trim()?2:0) + (inViewport(e)?1:0);
  const ordered=all.slice().sort((a,b)=>priority(b)-priority(a));
  const seen=new Set();
  const distinct=ordered.filter(e=>{
    if(e.tagName!=='A') return true;
    const key=e.href+'\n'+label(e);
    if(seen.has(key)) return false;
    seen.add(key);return true;
  });
  const nodes = distinct.slice(0, config.max_elements);
  const safeURL = value => { try { const u = new URL(value, location.href); u.search=''; u.hash=''; return u.href; } catch { return ''; } };
  const elements = nodes.map((e,i) => ({id:String(i), role:e.getAttribute('role') || e.tagName.toLowerCase(),
    bounds:(()=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})(), label:label(e), disabled:!!e.disabled || e.getAttribute('aria-disabled')==='true',
    href:e.tagName==='A' ? safeURL(e.href) : null,
    context:(e.closest('form,fieldset,section')?.getAttribute('aria-label') || e.closest('fieldset')?.querySelector('legend')?.innerText || '').trim().slice(0,80),
    editable:e.matches('input,textarea,select,[contenteditable=true]'),
    control_type:e.getAttribute('type') || (e.tagName==='BUTTON' ? e.type : ''),
    form_action:e.form?.action,form_method:e.form?.method,
    submits_form:!!e.form && ((e.tagName==='BUTTON' && e.type==='submit') || (e.tagName==='INPUT' && ['submit','image'].includes(e.type))),
    prepared_unique:e.matches('input,textarea') && Object.hasOwn(config.prepared_fields || {},label(e)) ? all.filter(n=>n.matches('input,textarea') && label(n)===label(e)).length===1 : undefined,
    prepared_matches:e.matches('input,textarea') && Object.hasOwn(config.prepared_fields || {},label(e)) ? e.value===config.prepared_fields[label(e)] : undefined,
    destination:e.tagName==='A' ? e.href : null,
    same_document:e.tagName==='A' && e.href.split('#')[0]===location.href.split('#')[0],
    region:inContent(e)?'content':'chrome',in_viewport:inViewport(e),
    image_link:!!e.querySelector('img'),
    media_destination:e.tagName==='A' && mediaDestinations.has(e.href),
    navigation:e.getAttribute('rel')==='next' || /^(next|previous)( page)?$/i.test(label(e))}));
  const version = crypto.randomUUID();
  const before = nodes.map(e => ({label:label(e), href:e.getAttribute('href'), disabled:!!e.disabled, role:e.getAttribute('role'), type:e.type,form:e.form,formAction:e.form?.action,formMethod:e.form?.method}));
  const pageURL = location.href;
  const supportedSource = e => { try { return !/\.(svg|ico)$/i.test(new URL(e.currentSrc).pathname); } catch { return false; } };
  const loadedImages=[...document.images].filter(e=>visible(e) && e.complete && supportedSource(e) && e.naturalWidth>=100 && e.naturalHeight>=64);
  const imagePriority = e => (inContent(e)?4:0)+(inViewport(e)?1:0);
  const imageNodes=loadedImages.sort((a,b)=>imagePriority(b)-imagePriority(a)).slice(0,30);
  const imageURLs=imageNodes.map(e=>e.currentSrc);
  const images=imageNodes.map((e,i)=>({id:String(i),label:(e.alt || e.title || e.closest('a')?.title || filename(e.currentSrc)).slice(0,160),url:safeURL(e.currentSrc),width:e.naturalWidth,height:e.naturalHeight,region:inContent(e)?'content':'chrome',in_viewport:inViewport(e)}));
  window.__jev = { prepare: action => {
    const e=nodes[Number(action.target)], state=before[Number(action.target)];
    if(action.version!==version || location.href!==pageURL || !e || !e.isConnected || !visible(e) || sensitive(e) || e.disabled || label(e)!==state.label || e.getAttribute('href')!==state.href) return null;
    e.scrollIntoView({block:'center',inline:'nearest'});
    const r=e.getBoundingClientRect(), x=r.x+r.width/2, y=r.y+r.height/2, hit=document.elementFromPoint(x,y);
    if(!hit || !(hit===e || e.contains(hit))) return null;
    return {x,y};
  }, execute: action => {
    if (action.version !== version || location.href !== pageURL) return 'stale';
    if (action.op==='SCROLL') { window.scrollBy(0, Math.max(300, innerHeight * .8)); return 'ok'; }
    const index = Number(action.target), e=nodes[index], state=before[index];
    if (!e || !e.isConnected || !visible(e) || sensitive(e) || e.disabled || e.getAttribute('aria-disabled')==='true') return 'stale';
    if (label(e)!==state.label || e.getAttribute('href')!==state.href || e.getAttribute('role')!==state.role || e.type!==state.type || e.form!==state.form || e.form?.action!==state.formAction || e.form?.method!==state.formMethod) return 'stale';
    if (action.op==='TYPE') {
      if (!e.matches('input,textarea') || typeof action.text!=='string' || action.text.length>2000) return 'type-blocked';
      const proto=e.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
      if (!setter) return 'type-blocked';
      setter.call(e,action.text);
      e.dispatchEvent(new Event('input',{bubbles:true}));
      e.dispatchEvent(new Event('change',{bubbles:true}));
      return 'ok';
    }
    if (e.matches('input,textarea,select,[contenteditable=true]')) return 'editable-blocked';
    e.scrollIntoView({block:'center',inline:'nearest'});
    const reachable=[...e.getClientRects()].some(r=>{
      const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      return hit && (hit===e || e.contains(hit));
    });
    if (!reachable) return 'covered';
    e.click(); return 'ok';
  }, image: action => {
    const e=imageNodes[Number(action.target)];
    if(action.version!==version || location.href!==pageURL || !e || !e.isConnected || !visible(e) || e.currentSrc!==imageURLs[Number(action.target)] || !e.complete) return null;
    const u=new URL(e.currentSrc);
    if(u.username || u.password || !['https:','http:'].includes(u.protocol)) return null;
    return e.currentSrc;
  }};
  // Text values from inputs are deliberately omitted. Page text may still be private.
  return {version,url:safeURL(location.href),title:document.title.slice(0,160),
    text:(document.body?.innerText || '').slice(0,config.text_limit),
    content_text:(content?.innerText || '').slice(0,config.text_limit), elements, images,
    pending_images:[...document.images].filter(e=>inContent(e) && visible(e) && (e.loading!=='lazy' || inViewport(e)) && !e.complete).length,
    scroll_y:Math.round(scrollY),scroll_height:document.documentElement.scrollHeight,viewport_height:innerHeight,
    total_elements:all.length,truncated:distinct.length>nodes.length, deduplicated:all.length-distinct.length, ready:document.readyState};
}
