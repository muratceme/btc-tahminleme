/* Fable sinyalleri: strateji seçimi, mum grafiği üzerinde giriş/çıkış işaretleri */
(function(){
var OFS=10800;
function saat(ts){var d=new Date((ts+OFS)*1000);return ('0'+d.getUTCHours()).slice(-2)+':'+('0'+d.getUTCMinutes()).slice(-2)}
function grafik(el,mumlar,rows){
  if(!window.LightweightCharts||el.dataset.cizildi)return;el.dataset.cizildi='1';
  var ch=LightweightCharts.createChart(el,{layout:{background:{color:'transparent'},textColor:'#9aa5b5'},
    grid:{vertLines:{color:'rgba(255,255,255,.04)'},horzLines:{color:'rgba(255,255,255,.04)'}},
    localization:{locale:'tr-TR',timeFormatter:function(t){return saat(t)+' TSİ'}},
    timeScale:{timeVisible:true,secondsVisible:false,tickMarkFormatter:function(t){return saat(t)}},
    rightPriceScale:{borderColor:'rgba(255,255,255,.1)'},height:340,crosshair:{mode:0}});
  var s=ch.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',wickUpColor:'#22c55e',wickDownColor:'#ef4444',borderVisible:false});
  s.setData(mumlar.map(function(m){return {time:m[0],open:m[1],high:m[2],low:m[3],close:m[4]}}));
  var M=[];
  rows.forEach(function(r){if(r.sinyal==='BEKLE')return;var t=Math.floor(new Date(r.zaman).getTime()/1000),L=r.sinyal==='LONG';
    M.push({time:t,position:L?'belowBar':'aboveBar',color:L?'#22c55e':'#ef4444',shape:L?'arrowUp':'arrowDown',text:L?'LONG':'SHORT'});
    if(r.cikis&&r.cikis.zaman){M.push({time:Math.floor(new Date(r.cikis.zaman).getTime()/1000),position:L?'aboveBar':'belowBar',
      color:r.cikis.net>0?'#fbbf24':'#9aa5b5',shape:'circle',text:(r.cikis.net>0?'+':'')+r.cikis.net.toFixed(2)+'%'})}});
  M.sort(function(a,b){return a.time-b.time});s.setMarkers(M);ch.timeScale().fitContent();
  new ResizeObserver(function(){ch.applyOptions({width:el.clientWidth})}).observe(el);
}
document.querySelectorAll('.fb-coin').forEach(function(kok){
  var V=window.FB&&window.FB[kok.dataset.sembol]||{mumlar:[],stratejiler:{}};
  var dugmeler=kok.querySelectorAll('.strat-dugme'),bloklar=kok.querySelectorAll('.strat');
  function sec(id){dugmeler.forEach(function(b){b.setAttribute('aria-pressed',b.dataset.strat===id)});
    bloklar.forEach(function(b){b.hidden=b.dataset.strat!==id;if(!b.hidden){var g=b.querySelector('.sz-grafik');
      if(g)setTimeout(function(){grafik(g,V.mumlar,V.stratejiler[id]||[])},0)}});try{localStorage.setItem('kr_strat',id)}catch(e){}}
  dugmeler.forEach(function(b){b.addEventListener('click',function(){sec(b.dataset.strat)})});
  var ilk=null;try{ilk=localStorage.getItem('kr_strat')}catch(e){}
  var qs=new URLSearchParams(location.search).get('strat');if(qs&&kok.querySelector('.strat[data-strat="'+qs+'"]'))ilk=qs;
  if(dugmeler.length){sec(ilk&&kok.querySelector('.strat[data-strat="'+ilk+'"]')?ilk:dugmeler[0].dataset.strat)}
  kok.querySelectorAll('.sz-hepsi').forEach(function(kutu){kutu.addEventListener('change',function(){kutu.closest('.strat').classList.toggle('bekle-goster',kutu.checked)})});
  kok.querySelectorAll('.serit i[data-satir]').forEach(function(h){h.addEventListener('click',function(){
    var tr=document.getElementById(h.dataset.satir);if(!tr)return;var st=tr.closest('.strat');st.classList.add('bekle-goster');var k=st.querySelector('.sz-hepsi');if(k)k.checked=true;
    tr.scrollIntoView({behavior:'smooth',block:'center'});tr.classList.add('vurgu');setTimeout(function(){tr.classList.remove('vurgu')},2000)})});
});
document.querySelectorAll('.coin').forEach(function(sec){
  var d=sec.querySelectorAll('.tf-dugme'),b=sec.querySelectorAll('.tf-blok');if(!d.length)return;
  function secTf(tf){d.forEach(function(y){y.setAttribute('aria-pressed',y.dataset.tf===tf)});b.forEach(function(y){y.hidden=y.dataset.tf!==tf})}
  d.forEach(function(x){x.addEventListener('click',function(){secTf(x.dataset.tf)})});
  var qt=new URLSearchParams(location.search).get('tf');if(qt&&sec.querySelector('.tf-blok[data-tf="'+qt+'"]'))secTf(qt)});
// sekme değişince gizli grafik çizilmemiş olabilir: görünür olunca çiz
new MutationObserver(function(){document.querySelectorAll('.fb-coin:not([hidden]) .strat:not([hidden]) .sz-grafik:not([data-cizildi])').forEach(function(g){
  var kok=g.closest('.fb-coin'),V=window.FB&&window.FB[kok.dataset.sembol];if(V)grafik(g,V.mumlar,V.stratejiler[g.dataset.stratGrafik]||[])})})
  .observe(document.body,{attributes:true,subtree:true,attributeFilter:['hidden']});
})();
