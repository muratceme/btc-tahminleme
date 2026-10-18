document.documentElement.classList.add('js');
(function(){
  var sek=document.querySelectorAll('.sekme'),coin=document.querySelectorAll('.coin');
  function sec(id){sek.forEach(function(s){s.setAttribute('aria-selected',s.dataset.hedef===id)});
    coin.forEach(function(c){c.hidden=c.id!==id});try{localStorage.setItem('kr_sekme',id)}catch(e){}}
  sek.forEach(function(s){s.addEventListener('click',function(){sec(s.dataset.hedef)})});
  var ilk=null;try{ilk=localStorage.getItem('kr_sekme')}catch(e){}
  var hs=location.hash.slice(1);if(hs&&document.getElementById(hs)&&document.querySelector('.sekme[data-hedef="'+hs+'"]'))ilk=hs;
  if(sek.length){sec(ilk&&document.getElementById(ilk)?ilk:sek[0].dataset.hedef)}
  var ts=document.body.dataset.ts?new Date(document.body.dataset.ts):null,yas=document.getElementById('yas'),
      saat=document.getElementById('saat'),nokta=document.getElementById('nokta');
  function tik(){var n=new Date();
    if(saat){saat.textContent=n.toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit',second:'2-digit'})+' TSİ'}
    if(ts&&yas){var dk=Math.max(0,Math.round((n-ts)/60000));yas.textContent=dk<1?'az önce':dk+' dk önce';
      if(nokta){nokta.classList.toggle('eski',dk>30);nokta.lastChild.textContent=dk>30?' ESKİ VERİ':' CANLI'}}}
  tik();setInterval(tik,1000);
  var y=parseInt(document.body.dataset.yenile||'0',10);
  if(y>0){try{var sy=sessionStorage.getItem('kr_scroll');if(sy){window.scrollTo(0,+sy);sessionStorage.removeItem('kr_scroll')}}catch(e){}
    setTimeout(function(){try{sessionStorage.setItem('kr_scroll',window.scrollY)}catch(e){}location.reload()},y*1000)}
})();
