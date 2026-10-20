(function(){
var OFS=10800, q=new URLSearchParams(location.search), S=q.get('s')||'', K=q.get('k')||'';
var $=function(id){return document.getElementById(id)};
function hata(m){$('icerik').innerHTML='<div class="kart"><p>'+m+'</p><p class="kucuk"><a href="rapor.html">← Panoya dön</a></p></div>'}
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function tarih(t){var d=new Date((t+OFS)*1000);return d.toISOString().slice(0,16).replace('T',' ')}
function fiyat(x){return x==null?'—':(x>=100?x.toLocaleString('tr-TR',{maximumFractionDigits:2}):x.toLocaleString('tr-TR',{maximumFractionDigits:5}))}
if(!/^[A-Z0-9]+_[0-9]+m$/.test(S)){hata('Geçersiz adres.');return}
if(typeof LightweightCharts==='undefined'){hata('Grafik kütüphanesi yüklenemedi (cikti/statik klasörü eksik). Raporu yeniden üret.');return}
var sc=document.createElement('script');sc.src='veri/'+S+'.js?'+Date.now();
sc.onerror=function(){hata('Grafik verisi bulunamadı. Önce raporu üret: <span class="mono">python -m btc_tahmin rapor</span>')};
sc.onload=function(){var D=(window.KR||{})[S];if(!D){hata('Veri okunamadı.');return}var R=D.kurallar[K];
  if(!R){hata('Bu kural güncel raporda yok (kurallar her gün yeniden aranır). Panodan yeni bir kural seç.');return}ciz(D,R)};
document.head.appendChild(sc);

function ciz(D,R){
  var up=R.yukselis, sinif=up?'iyi':'kotu', BOL=['Eğitim','Doğrulama','Test','ŞU AN'];
  document.title=D.sembol.replace('USDT','')+' · '+R.hedef+' · Kural grafiği';
  var O=R.olusumlar, biten=O.filter(function(o){return o[2]>=0}), tut=biten.filter(function(o){return o[2]===1});
  function oran(a){var t=a.filter(function(o){return o[2]===1}).length;return a.length?(100*t/a.length).toFixed(0)+'%':'—'}
  function ort(a,k){k=k||5;if(!a.length)return '—';var s=0;a.forEach(function(o){s+=o[k]});return (s/a.length>=0?'+':'')+(s/a.length).toFixed(2)+'%'}
  function topla(a){var s=0;a.forEach(function(o){s+=o[6]});return s}
  var tutmayan=biten.filter(function(o){return o[2]===0}), aktif=O.some(function(o){return o[1]===3});
  var cips=R.kosullar.map(function(k){return '<span class="cip '+k.egilim+'" title="'+esc(k.aciklama)+'">'+esc(k.etiket)+'</span>'}).join('');
  $('icerik').innerHTML=
   '<div class="kart bolum"><div class="kart-baslik"><span>'+esc(D.sembol)+' · '+esc(D.aralik)+' · kural grafiği</span><a href="rapor.html" class="kucuk">← Panoya dön</a></div>'+
   '<div class="kural-ust"><span class="rozet '+sinif+'">'+(up?'▲ ':'▼ ')+esc(R.hedef)+'</span><span class="kural-yuzde '+sinif+'">%'+Math.round(R.tutarlilik*100)+'</span>'+
   '<span class="kucuk">test tutarlılığı · '+R.kosullar.length+' koşul'+(aktif?' · <b class="altin">ŞU AN AKTİF</b>':'')+'</span></div>'+
   '<div style="margin-top:6px">'+cips+'</div>'+
   '<p class="satir-not">Aşağıdaki grafikte bu koşulların <b>tüm geçmişte</b> aynı anda oluştuğu her an işaretli. '+
   '<span class="iyi">Yeşil ok</span> = tuttu, <span class="kotu">kırmızı daire</span> = tutmadı, <span class="altin">altın</span> = şu an aktif (sonuç bekleniyor). '+
   (R.blok>1?'Birbirine '+R.blok+' mumdan yakın tekrarlar tek sayılır (aynı mumları paylaştıkları için).':'')+' Saatler TSİ.</p></div>'+
   '<div class="izgara-4 kpi-4">'+
    kpi('Tüm zamanlar',tut.length+' / '+biten.length,'isabet '+oran(biten))+
    kpi('Eğitim · doğrulama',oran(biten.filter(function(o){return o[1]===0}))+' · '+oran(biten.filter(function(o){return o[1]===1})),'kuralın bulunduğu ve elendiği dönemler')+
    kpi('Test (hiç görülmemiş)',oran(biten.filter(function(o){return o[1]===2})),'n = '+biten.filter(function(o){return o[1]===2}).length+' · normal oran %'+Math.round(R.taban_oran*100))+
    kpi('Net kazanç (komisyonlu)',ort(biten,6),'işlem başı ort. · maliyet %'+R.maliyet+' · toplam '+(topla(biten)>=0?'+':'')+topla(biten).toFixed(1)+'% · fiyat tuttuğunda '+ort(tut)+' / tutmadığında '+ort(tutmayan))+
   '</div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Mum grafiği · tüm oluşumlar</span>'+
   '<div class="filtre" id="filtre"><button data-f="hepsi" aria-pressed="true">Tümü</button><button data-f="test">Sadece test</button>'+
   '<button data-f="tuttu">Tuttu</button><button data-f="tutmadi">Tutmadı</button></div></div>'+
   '<div id="grafik" class="grafik-kutu"></div><p class="cok-kucuk">Tekerlekle yakınlaş, sürükleyerek kaydır. Tablodaki bir satıra tıklayınca grafik o ana gider.</p></div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Zaman içinde isabet · birikimli</span></div>'+
   '<div id="grafik2" class="grafik-kucuk"></div><p class="cok-kucuk">Çizgi yatay ve yüksek kalıyorsa kural her dönemde tutmuş demektir. Sona doğru düşüyorsa kural zayıflıyor olabilir. Kesikli çizgi: normal (rastgele) oran.</p></div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Tüm oluşumlar ('+O.length+') · en yeni üstte</span></div><div class="tablo-sar" style="max-height:460px;overflow-y:auto"><table><thead><tr>'+
   '<th>Tarih (TSİ)</th><th>Dönem</th><th class="sayi">Giriş</th><th class="sayi">Çıkış</th><th class="sayi">Fiyat değişimi</th><th class="sayi">Net işlem</th><th>Sonuç</th></tr></thead><tbody id="tablo"></tbody></table></div></div>';

  var renk={yazi:'#8b97a9',cizgi:'rgba(148,163,184,.08)',kenar:'rgba(148,163,184,.22)'};
  var ortak={layout:{background:{type:'solid',color:'transparent'},textColor:renk.yazi,fontFamily:'JetBrains Mono, monospace'},
    grid:{vertLines:{color:renk.cizgi},horzLines:{color:renk.cizgi}},rightPriceScale:{borderColor:renk.kenar},
    timeScale:{borderColor:renk.kenar,timeVisible:true,secondsVisible:false},crosshair:{mode:0},autoSize:true,
    localization:{locale:'tr-TR',dateFormat:'dd.MM.yy'}};
  var ch=LightweightCharts.createChart($('grafik'),ortak);
  var mum=ch.addCandlestickSeries({upColor:'#16c784',downColor:'#ea3943',borderVisible:false,wickUpColor:'#16c784',wickDownColor:'#ea3943'});
  var zam=D.mumlar.map(function(m){return m[0]});
  mum.setData(D.mumlar.map(function(m){return {time:m[0]+OFS,open:m[1],high:m[2],low:m[3],close:m[4]}}));
  function isaret(f){var L=O.filter(function(o){return f==='hepsi'||(f==='test'&&o[1]>=2)||(f==='tuttu'&&o[2]===1)||(f==='tutmadi'&&o[2]===0)});
    mum.setMarkers(L.map(function(o){var bek=o[2]<0;return {time:o[0]+OFS,position:up?'belowBar':'aboveBar',
      color:bek?'#f3d778':(o[2]===1?'#16c784':'#ea3943'),shape:bek?'square':(o[2]===1?(up?'arrowUp':'arrowDown'):'circle'),
      text:bek?'ŞİMDİ':''}}))}
  isaret('hepsi');
  function git(t){var lo=0,hi=zam.length-1;while(lo<hi){var m=(lo+hi)>>1;if(zam[m]<t)lo=m+1;else hi=m}
    ch.timeScale().setVisibleLogicalRange({from:lo-70,to:lo+40});window.scrollTo({top:$('grafik').getBoundingClientRect().top+scrollY-120,behavior:'smooth'})}
  if(O.length){var t0=O[O.length-1][0],lo=0,hi=zam.length-1;while(lo<hi){var m=(lo+hi)>>1;if(zam[m]<t0)lo=m+1;else hi=m}
    ch.timeScale().setVisibleLogicalRange({from:lo-70,to:lo+40})}
  document.querySelectorAll('#filtre button').forEach(function(b){b.addEventListener('click',function(){
    document.querySelectorAll('#filtre button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});isaret(b.dataset.f)})});

  var ch2=LightweightCharts.createChart($('grafik2'),ortak), taban=R.taban_oran*100,
    cizgi=ch2.addLineSeries({color:'#f3d778',lineWidth:2,priceFormat:{type:'percent'},
      autoscaleInfoProvider:function(f){var r=f();if(!r)return r;r.priceRange.minValue=Math.min(r.priceRange.minValue,taban-5);r.priceRange.maxValue=Math.max(r.priceRange.maxValue,100);return r}});
  var h=0,n=0,nokta=[];biten.forEach(function(o){n++;h+=o[2];nokta.push({time:o[0]+OFS,value:100*h/n})});
  var tekil=[];nokta.forEach(function(p){if(tekil.length&&tekil[tekil.length-1].time===p.time)tekil[tekil.length-1]=p;else tekil.push(p)});
  cizgi.setData(tekil);cizgi.createPriceLine({price:R.taban_oran*100,color:'#8b97a9',lineStyle:2,lineWidth:1,axisLabelVisible:true,title:'normal'});
  ch2.timeScale().fitContent();

  var satir=O.slice().reverse().map(function(o){var s=o[2]<0?'<span class="rozet altin">BEKLENİYOR</span>':(o[2]===1?'<span class="rozet iyi">✓ TUTTU</span>':'<span class="rozet kotu">✕ TUTMADI</span>');
    var d=o[5]==null?'—':'<span class="'+(o[5]>=0?'iyi':'kotu')+'">'+(o[5]>=0?'+':'')+o[5].toFixed(2)+'%</span>';
    return '<tr class="tik" data-t="'+o[0]+'"><td class="mono">'+tarih(o[0])+'</td><td>'+BOL[o[1]]+'</td><td class="sayi mono">'+fiyat(o[3])+'</td><td class="sayi mono">'+fiyat(o[4])+'</td><td class="sayi mono">'+d+'</td><td class="sayi mono">'+(o[6]==null?'—':'<span class="'+(o[6]>=0?'iyi':'kotu')+'">'+(o[6]>=0?'+':'')+o[6].toFixed(2)+'%</span>')+'</td><td>'+s+'</td></tr>'}).join('');
  $('tablo').innerHTML=satir;
  $('tablo').addEventListener('click',function(e){var tr=e.target.closest('tr');if(!tr)return;
    document.querySelectorAll('#tablo tr.secili').forEach(function(x){x.classList.remove('secili')});tr.classList.add('secili');git(+tr.dataset.t)});
}
function kpi(e,d,a){return '<div class="kart"><div class="kart-baslik"><span>'+e+'</span></div><div class="dev" style="font-size:30px">'+d+'</div><div class="kucuk">'+a+'</div></div>'}
})();
