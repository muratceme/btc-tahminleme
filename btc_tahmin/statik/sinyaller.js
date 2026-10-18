/* Sinyaller sayfası: mum grafiği üzerinde giriş/çıkış işaretleri, zaman şeridi ve tablo filtreleri */
(function(){
var OFS=10800;
function saat(ts){var d=new Date((ts+OFS)*1000);return ('0'+d.getUTCHours()).slice(-2)+':'+('0'+d.getUTCMinutes()).slice(-2)}
function grafik(kok){
  var V=window.SZ&&window.SZ[kok.dataset.sembol];if(!V||!window.LightweightCharts)return;
  var el=kok.querySelector('.sz-grafik');
  var ch=LightweightCharts.createChart(el,{layout:{background:{color:'transparent'},textColor:'#9aa5b5'},
    grid:{vertLines:{color:'rgba(255,255,255,.04)'},horzLines:{color:'rgba(255,255,255,.04)'}},
    localization:{locale:'tr-TR',timeFormatter:function(t){return saat(t)+' TSİ'}},
    timeScale:{timeVisible:true,secondsVisible:false,tickMarkFormatter:function(t){return saat(t)}},
    rightPriceScale:{borderColor:'rgba(255,255,255,.1)'},height:360,crosshair:{mode:0}});
  var s=ch.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',wickUpColor:'#22c55e',wickDownColor:'#ef4444',borderVisible:false});
  s.setData(V.mumlar.map(function(m){return {time:m[0],open:m[1],high:m[2],low:m[3],close:m[4]}}));
  function isaretle(ufuk){
    var M=[];
    V.cizelge.forEach(function(r){var u=r[ufuk];if(!u||u.sinyal==='BEKLE')return;
      var t=Math.floor(new Date(r.zaman).getTime()/1000),L=u.sinyal==='LONG';
      M.push({time:t,position:L?'belowBar':'aboveBar',color:L?'#22c55e':'#ef4444',shape:L?'arrowUp':'arrowDown',text:(L?'L':'S')+(u.cikis_mum?' →'+u.cikis_mum:'')});
      if(u.cikis&&u.cikis.zaman){var ct=Math.floor(new Date(u.cikis.zaman).getTime()/1000);
        M.push({time:ct,position:L?'aboveBar':'belowBar',color:u.cikis.net>0?'#fbbf24':'#9aa5b5',shape:'circle',text:(u.cikis.net>0?'+':'')+u.cikis.net.toFixed(2)+'%'})}});
    M.sort(function(a,b){return a.time-b.time});s.setMarkers(M)}
  isaretle('kisa');ch.timeScale().fitContent();
  kok.querySelectorAll('[data-ufuk]').forEach(function(b){b.addEventListener('click',function(){
    kok.querySelectorAll('[data-ufuk]').forEach(function(x){x.setAttribute('aria-pressed',x===b)});isaretle(b.dataset.ufuk)})});
  new ResizeObserver(function(){ch.applyOptions({width:el.clientWidth})}).observe(el);
}
document.querySelectorAll('.sz-coin').forEach(function(kok){
  grafik(kok);
  var kutu=kok.querySelector('.sz-hepsi');
  if(kutu){kutu.addEventListener('change',function(){kok.classList.toggle('bekle-goster',kutu.checked)})}
  kok.querySelectorAll('.serit i[data-satir]').forEach(function(h){h.addEventListener('click',function(){
    var tr=document.getElementById(h.dataset.satir);if(!tr)return;kok.classList.add('bekle-goster');if(kutu)kutu.checked=true;
    tr.scrollIntoView({behavior:'smooth',block:'center'});tr.classList.add('vurgu');setTimeout(function(){tr.classList.remove('vurgu')},2000)})});
});
})();
