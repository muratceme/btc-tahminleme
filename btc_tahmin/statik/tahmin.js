/* Mum tahmini: gerçek mumlar + 1 mum ileri tahmin çizgisi (son gün) + gelecek yolu ve bant */
(function(){
var OFS=10800;
function saat(ts){var d=new Date((ts+OFS)*1000);return ('0'+d.getUTCHours()).slice(-2)+':'+('0'+d.getUTCMinutes()).slice(-2)}
function ciz(kok){
  var V=window.TH&&window.TH[kok.dataset.sembol];var el=kok.querySelector('.sz-grafik');if(!V||!el||!window.LightweightCharts||el.dataset.cizildi)return;
  el.dataset.cizildi='1';
  var mumlar=(window.MUM&&window.MUM[V.mum])||[];
  var ch=LightweightCharts.createChart(el,{layout:{background:{color:'transparent'},textColor:'#9aa5b5'},
    grid:{vertLines:{color:'rgba(255,255,255,.04)'},horzLines:{color:'rgba(255,255,255,.04)'}},
    localization:{locale:'tr-TR',timeFormatter:function(t){return saat(t)+' TSİ'}},
    timeScale:{timeVisible:true,secondsVisible:false,tickMarkFormatter:function(t){return saat(t)},rightOffset:10},
    rightPriceScale:{borderColor:'rgba(255,255,255,.1)'},height:380,crosshair:{mode:0}});
  var s=ch.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',wickUpColor:'#22c55e',wickDownColor:'#ef4444',borderVisible:false});
  s.setData(mumlar.map(function(m){return {time:m[0],open:m[1],high:m[2],low:m[3],close:m[4]}}));
  var sure=V.tahmin.gecmis.length>1?V.tahmin.gecmis[1].zaman-V.tahmin.gecmis[0].zaman:900;
  var t1=ch.addLineSeries({color:'#fbbf24',lineWidth:2,priceLineVisible:false,lastValueVisible:false,title:'1 mum ileri tahmin'});
  t1.setData(V.tahmin.gecmis.map(function(g){return {time:g.zaman+sure,value:g.tahmin_1}}));
  var yol=ch.addLineSeries({color:'#60a5fa',lineWidth:2,lineStyle:2,priceLineVisible:false,title:'tahmin yolu'});
  var alt=ch.addLineSeries({color:'rgba(96,165,250,.45)',lineWidth:1,lineStyle:1,priceLineVisible:false,lastValueVisible:false});
  var ust=ch.addLineSeries({color:'rgba(96,165,250,.45)',lineWidth:1,lineStyle:1,priceLineVisible:false,lastValueVisible:false});
  var bas={time:V.tahmin.simdi.zaman,value:V.tahmin.simdi.kapanis};
  yol.setData([bas].concat(V.tahmin.yol.map(function(y){return {time:y.zaman,value:y.tahmin}})));
  alt.setData([bas].concat(V.tahmin.yol.filter(function(y){return y.alt!=null}).map(function(y){return {time:y.zaman,value:y.alt}})));
  ust.setData([bas].concat(V.tahmin.yol.filter(function(y){return y.ust!=null}).map(function(y){return {time:y.zaman,value:y.ust}})));
  ch.timeScale().fitContent();
  new ResizeObserver(function(){ch.applyOptions({width:el.clientWidth})}).observe(el);
}
document.querySelectorAll('.tahmin-coin').forEach(function(k){if(!k.hidden)ciz(k)});
new MutationObserver(function(){document.querySelectorAll('.tahmin-coin:not([hidden])').forEach(ciz)}).observe(document.body,{attributes:true,subtree:true,attributeFilter:['hidden']});
})();
