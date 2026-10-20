/* TV modu: sayfaları sırayla döndür, rakamla atla, boşlukla durdur, F tam ekran, +/- yakınlaştır */
(function(){
  var S=window.TV||[],q=new URLSearchParams(location.search),sn=parseInt(q.get('sn')||'45',10),i=0,dur=false,kalan=sn,zoom=parseFloat(q.get('zoom')||'1.25');
  var cer=document.getElementById('cerceve'),serit=document.getElementById('serit'),sayac=document.getElementById('sayac'),ilerleme=document.getElementById('ilerleme');
  try{var k=localStorage.getItem('kr_tv_zoom');if(k)zoom=parseFloat(k)}catch(e){}
  function yakinlastir(){try{cer.contentDocument.documentElement.style.zoom=zoom;cer.contentDocument.documentElement.classList.add('tv')}catch(e){}}
  cer.addEventListener('load',yakinlastir);
  function git(n){i=(n+S.length)%S.length;kalan=sn;cer.src=S[i].u+'?tv=1';
    serit.querySelectorAll('a[data-i]').forEach(function(a){a.classList.toggle('aktif',+a.dataset.i===i)});goster()}
  function goster(){serit.classList.remove('gizli');clearTimeout(goster.t);goster.t=setTimeout(function(){serit.classList.add('gizli')},6000)}
  serit.querySelectorAll('a[data-i]').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();git(+a.dataset.i)})});
  document.getElementById('dur').addEventListener('click',function(e){e.preventDefault();dur=!dur;this.textContent=dur?'▶':'⏸';goster()});
  setInterval(function(){if(!dur){kalan--;if(kalan<=0){git(i+1)}}sayac.textContent=(dur?'durduruldu':'sonraki '+kalan+' sn')+' · '+(i+1)+'/'+S.length;
    ilerleme.style.width=(dur?0:(100*(sn-kalan)/sn))+'%'},1000);
  document.addEventListener('keydown',function(e){
    if(/^[1-9]$/.test(e.key)){var n=+e.key-1;if(n<S.length)git(n)}
    else if(e.key==='ArrowRight'||e.key==='PageDown'||e.key==='MediaTrackNext')git(i+1);
    else if(e.key==='ArrowLeft'||e.key==='PageUp'||e.key==='MediaTrackPrevious')git(i-1);
    else if(e.key===' '||e.key==='MediaPlayPause'||e.key==='Enter'){e.preventDefault();document.getElementById('dur').click()}
    else if(e.key==='f'||e.key==='F'){(document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()).catch(function(){})}
    else if(e.key==='+'||e.key==='='){zoom=Math.min(2,zoom+0.1);yakinlastir();try{localStorage.setItem('kr_tv_zoom',zoom)}catch(x){}}
    else if(e.key==='-'){zoom=Math.max(0.8,zoom-0.1);yakinlastir();try{localStorage.setItem('kr_tv_zoom',zoom)}catch(x){}}
    else return;goster()});
  document.addEventListener('mousemove',goster);
  git(parseInt(q.get('s')||'1',10)-1);
})();
