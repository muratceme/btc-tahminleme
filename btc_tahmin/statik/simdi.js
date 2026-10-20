/* Şimdi gir: bölüm sekmeleri (son mum / son 1 saat), yeni sinyalde tarayıcı bildirimi + ses */
(function(){
  var dug=document.querySelectorAll('.simdi-sekme'),bol=document.querySelectorAll('.simdi-bolum');
  function sec(id){dug.forEach(function(d){d.setAttribute('aria-pressed',d.dataset.bolum===id)});bol.forEach(function(b){b.hidden=b.dataset.bolum!==id});
    try{localStorage.setItem('kr_simdi_bolum',id)}catch(e){}}
  dug.forEach(function(d){d.addEventListener('click',function(){sec(d.dataset.bolum);history.replaceState(null,'','#'+d.dataset.bolum)})});
  var h=location.hash.slice(1),ilk=null;try{ilk=localStorage.getItem('kr_simdi_bolum')}catch(e){}
  if(h==='son-saat'||h==='son-mum')ilk=h;if(ilk&&document.querySelector('.simdi-bolum[data-bolum="'+ilk+'"]'))sec(ilk);

  // Bildirim: sayfa her dakika yenilenir; sinyal sayısı önceki yüklemeden büyükse uyar
  var n=parseInt(document.body.dataset.sinyal||'0',10),onceki=null;try{onceki=localStorage.getItem('kr_simdi_sinyal')}catch(e){}
  var btn=document.getElementById('bildirim-ac'),ses=document.getElementById('ses-ac');
  try{ses.checked=localStorage.getItem('kr_ses')!=='0'}catch(e){}
  if(ses){ses.addEventListener('change',function(){try{localStorage.setItem('kr_ses',ses.checked?'1':'0')}catch(e){}})}
  function durumYaz(){if(!btn)return;if(!('Notification' in window)){btn.textContent='🔔 tarayıcı desteklemiyor';btn.disabled=true;return}
    btn.textContent=Notification.permission==='granted'?'🔔 Bildirimler açık':(Notification.permission==='denied'?'🔕 Bildirim engelli (tarayıcı ayarı)':'🔔 Bildirimleri aç')}
  durumYaz();
  if(btn){btn.addEventListener('click',function(){if('Notification' in window&&Notification.permission!=='granted'){Notification.requestPermission().then(durumYaz)}
    bip()})}
  function bip(){if(ses&&!ses.checked)return;try{var A=window.AudioContext||window.webkitAudioContext;if(!A)return;var c=new A(),o=c.createOscillator(),g=c.createGain();
    o.type='sine';o.frequency.value=880;g.gain.value=0.08;o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+0.18);
    setTimeout(function(){var o2=c.createOscillator();o2.frequency.value=1320;o2.connect(g);o2.start();o2.stop(c.currentTime+0.18)},220)}catch(e){}}
  if(onceki!==null&&n>parseInt(onceki,10)){
    if('Notification' in window&&Notification.permission==='granted'){try{new Notification('Kripto Risk Terminali',{body:'Son mumda '+n+' kaynakta sinyal var. Şimdi gir sayfasına bak.'})}catch(e){}}
    bip()}
  try{localStorage.setItem('kr_simdi_sinyal',String(n))}catch(e){}
})();
