# btc-tahminleme — Kripto Risk Terminali

BTC, ETH ve XRP için **15m / 10m** mumlarda onlarca indikatör, mum formasyonu, üst zaman dilimi trendi,
coinler arası ilişki ve seans bilgisini tarar. Çıktı olarak **gün sonu risk oranları** üretir. Her oranın yanında
bir **tutarlılık** değeri bulunur: o oranın, modelin hiç görmediği test döneminde ne sıklıkla doğru çıktığı.

```
Risk-A  Tutarlılık %91   Long risk %24   (GradientBoost, gün sonu)
Risk-B  Tutarlılık %84   Long risk %31   (Kombinasyon: RSI:30-45 + MACD_HIST:negatif_artan + SUPERTREND:boga + ...)
Risk-C  Tutarlılık %80   max düşüş -1.9% (Volatilite rejimi)
...       (%70 altında hiçbir satır gösterilmez)
```

## Kurulum (bir kez)

```bash
git clone https://github.com/muratceme/btc-tahminleme.git
cd btc-tahminleme
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
Python 3.10 veya daha yenisi gerekir. API anahtarı gerekmez; tüm kaynaklar herkese açık uç noktalar.

## Kullanım

| Komut | Ne yapar |
|---|---|
| `python -m btc_tahmin rapor --ac` | Veriyi indirir/günceller, her şeyi analiz eder, panoyu tarayıcıda açar |
| `python -m btc_tahmin rapor --aralik 10m` | 10 dakikalık mumlarla (5m'den üretilir) |
| `python -m btc_tahmin rapor --hizli` | Son 24 saatte bulunan kuralları yeniden kullanır (~1 dk) |
| `python -m btc_tahmin rapor --coin BTC` | Sadece seçilen coin(ler) |
| `python -m btc_tahmin canli --ac` | **Önerilen.** Her 15m mumda yeniler, 24 saatten yeni kural önbelleği varsa onu kullanır (yeniden açılış 1-2 dk; `--tam` ile kuralları şimdi yeniden aratırsın), panoyu **http://localhost:8000** adresinde yayınlar. Aynı Wi-Fi'daki telefondan terminalde yazan `http://192.168.x.x:8000` adresiyle açılır |
| `python -m btc_tahmin izle --dakika 15 --ac` | Her 15m mum kapanışında otomatik yeniler, pano dakikada bir tazelenir |
| `python -m btc_tahmin ozet` | Son raporu terminalde tekrar gösterir |
| `python -m btc_tahmin canli --tunel` | Evden dışarıdan (mobil veriyle) erişim: Cloudflare tüneliyle `https://….trycloudflare.com` adresi açar, panoyu otomatik şifreler. Bir kez `winget install --id Cloudflare.cloudflared` gerekir |
| `python -m btc_tahmin telegram` | Telefona bildirim kurulumu (adım adım). Sonra güçlü sinyaller Telegram'a mesaj olarak gelir |
| `python -m btc_tahmin karne` | **Canlı karne:** sistemin gerçek sinyallerinin isabeti ve komisyon sonrası net sonucu |
| `python -m btc_tahmin sahte --tekrar 5` | **Sahte keşif testi:** bulunan kuralların kaçı şans eseri olabilir? Hedefleri tam gün kaydırıp madenciliği 5 kez tekrarlar (coin başına ~5-15 dk). Sonuç panoda ve Veri durumu panelinde görünür |
| `python -m btc_tahmin rapor --aralik 1h` | Diğer zaman dilimleri: 5m, 10m, 15m, 30m, 1h, 4h |
| `python -m btc_tahmin kontrol` | **Her metrik geldi mi?** ✓ geldi / ○ boş ama normal / ✗ hata (sebebiyle). `--kaynaklar` ile dış kaynakları şimdi tekrar dener |

Kısa yollar: Windows'ta `calistir.bat`, macOS/Linux'ta `./calistir.sh`. İkisi de `canli` modunu başlatır.

**Telefondan bakmak:** Telefon ile bilgisayar aynı Wi-Fi'da olmalı. Terminalde yazan `TELEFONDAN` adresini telefonun
tarayıcısına yaz. Windows "erişime izin ver" diye sorarsa **Özel ağlar** kutusunu işaretleyip izin ver.
Bilgisayar açık ve pencere açık olduğu sürece pano güncel kalır.

**Claude Code ile:** repo klasöründe `claude` açıp `/btc-rapor` yaz. Rapor üretilir ve Wall Street brifingi
formatında özetlenir. Sürekli takip için: `/loop 15m /btc-rapor hizli`. Kırım eklemek için:
`/btc-rapor kirim: Fed belirsizliği 5`.

İlk çalıştırma yaklaşık 540 günlük veri indirir ve kural madenciliği yapar (derin tarama dahil coin başına ~1-2 dk). Toplam 5-10 dakika sürebilir.
Sonraki çalıştırmalar sadece yeni mumları indirir.

## Çıktılar (`cikti/`)

- `rapor.html`: Bloomberg terminali tarzı koyu pano. Kayan fiyat/dominans/haber şeridi, CANLI göstergesi, coin sekmeleri,
  yarım daire risk göstergesi ve karar etiketi, "bu risk neye dayanıyor" açıklaması, risk tablosu (her satırın düz Türkçe anlamıyla),
  aktif kombinasyon kartları, sinyal haritası (şu an doğru olan tüm koşullar gruplu ve renkli)
- **Derin tarama (%85+):** 3-7 indikatörün ince eşiklerle (RSI 35-40, CCI −150..−100 …) aynı anda oluştuğu kombinasyonlar.
  Hedefler: sonraki mum, 2/3/4/8 mum sonra fiyat yönü, sonraki 2-3 mumun hepsi yeşil/kırmızı. Sadece hiç görülmemiş test
  döneminde %85 ve üzeri tutanlar gösterilir.
- `grafik.html`: Her kuralın **📈 Grafikte incele** butonu. Mum grafiğinde kuralın tüm geçmiş oluşumları (tuttu / tutmadı / şu an),
  dönem dönem isabet, birikimli isabet çizgisi ve tıklanabilir oluşum tablosu. Grafik: TradingView Lightweight Charts (Apache 2.0, repoya gömülü)
- `nasil-calisir.html`: Her şeyin nasıl hesaplandığını anlatan rehber: veriler, tüm indikatör ve formasyonlar, kombinasyon arama,
  tutarlılık ölçümü, risk türleri, kırım tablosu, dominans okuma, örnekli okuma rehberi, sözlük. Panodaki `?` işaretleri buraya götürür
- `rapor.json`: tüm sayılar (başka araçlara bağlamak için)
- `kurallar_BTCUSDT_15m.csv`: bulunan tüm kombinasyon kuralları ve test istatistikleri

## Para tarafı: komisyon, simülasyon, karne, pozisyon

- **Yön sinyali (LONG / SHORT / BEKLE):** O an aktif olan tüm tutarlı kural ve modellerin oylaması. İki ayrı ufuk vardır:
  **kısa vade** (sonraki mum, 2-8 mum sonra, seri mumlar) ve **gün sonu**; farklı vadeler aynı oya karıştırılmaz.
  Her kaynağın ağırlığı tutarlılığının **Wilson alt sınırı** − 0,5'tir: az örnekli bir kural, aynı yüzdeyle çok örnekli
  bir kuraldan daha az söz hakkı alır. Coin sekmesinde ve her coinin üstünde görünür.
- **Geriye dönük kontrol:** 15, 30, 45 ve 60 dakika önce sistem hangi sinyali veriyordu, o an long ya da short açsaydın
  şu anki fiyatla komisyon dahil ne durumda olurdun.

- **Komisyon sonrası net kazanç:** Her kural işlem gibi hesaplanır (giriş: sinyal mumu kapanışı, çıkış: hedefin bittiği mum).
  Maliyet vadeli için işlem başı %0,14, spot için %0,24 (komisyon + kayma); vadelide pozisyonun açık kaldığı her 8 saat için
  funding (%0,01) da eklenir. Test döneminde komisyondan sonra zarar ettiren kural **"KOMİSYONA YENİLİYOR"** diye işaretlenir
  (ayarlarda `"net_zararli_kurallari_ele": true` ile tamamen gizlenir).
  Kartlarda ortalama net, kâr faktörü ve son 20 oluşumdaki isabet yazar; düşüşteyse **ZAYIFLIYOR** rozeti çıkar.
- **Kasa simülasyonu:** "Test döneminde bu sinyallere uysaydım 1.000$ ne olurdu?" Bakiye eğrisi, en kötü düşüş, aynı dönemde al-tut kıyası.
  Kurallar bu dönem de dahil seçildiği için iyimserdir.
- **Canlı karne:** Canlı modda her sinyal `veri/sinyal_gunlugu.csv` dosyasına kaydedilir, süresi dolunca gerçek fiyatla sonuçlandırılır.
  Canlı isabet beklenenle yan yana gösterilir. Canlıda kötü giden kurallar (10+ sinyal, isabet %55 altı) otomatik emekliye ayrılır.
- **Pozisyon hesaplayıcı:** Net gün sonu sinyali varsa kasana göre pozisyon büyüklüğü, stop (gün içi en kötü hareket sınırının ötesi)
  ve hedef (1:1,5) hesaplanır. Riske edilen tutar genel piyasa puanıyla küçülür.

### Kişisel ayarlar

`ayarlar/kullanici.ornek.json` dosyasını `ayarlar/kullanici.json` adıyla kopyala ve düzenle:

```json
{"islem_turu": "vadeli", "kasa_usd": 1000, "islem_basi_risk_yuzde": 1, "max_kaldirac": 3,
 "semboller": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT"],
 "telegram": {"token": "", "chat_id": "", "min_tutarlilik": 0.80}}
```
`kullanici.json` git'e gönderilmez; Telegram anahtarın gizli kalır. `semboller` ile SOL, BNB gibi coin ekleyebilirsin.

## Neye bakıyor?

**İndikatörler:** RSI(14/7), Stochastic, StochRSI, MACD (histogram yönü, kesişimler, sıfır çizgisi), EMA 9/21/50/100/200 ve dizilimi,
Bollinger (%B, sıkışma), ADX/DI, CCI, MFI, Williams %R, ATR/volatilite rejimi, OBV eğimi, Supertrend, Ichimoku (bulut, TK),
günlük VWAP, Keltner, momentum (ROC), hacim z-skoru, taker alış oranı (alıcı/satıcı baskısı).

**Formasyonlar:** doji, çekiç, ters çekiç, kayan yıldız, asılı adam, yutan boğa/ayı, harami, sabah/akşam yıldızı,
üç beyaz asker / üç kara karga, marubozu, iç/dış mum, pin bar, cımbız dip/tepe, delici hat, kara bulut,
20 mumluk kırılımlar, ikili dip/tepe, yükselen dipler / alçalan tepeler.

**Bağlam:** 1s ve 4s trend/RSI/Supertrend, diğer coinlerin momentumu ve BTC paritesi (ETH/BTC, XRP/BTC),
seans (Asya/Avrupa/ABD), hafta sonu.

**Piyasa geneli (puan kırımı için):** BTC.D, ETH.D, XRP.D, USDT.D, USDC.D, stablecoin toplamı, OTHERS.D,
toplam piyasa değeri, Korku/Açgözlülük endeksi, funding oranı, açık pozisyon (OI) değişimi, long/short oranı,
taker alış/satış, likidasyon tahmini (OI + fiyat), haber başlıkları (6 kaynak, anahtar kelime skoru),
Nasdaq/S&P vadeli, dolar endeksi, altın, ABD 10Y faiz ve BTC ile korelasyonları, spot BTC/ETH ETF akışları (deneysel),
Deribit opsiyon put/call oranı ve max pain, otomatik ABD ekonomik takvimi (ForexFactory) + elle girilen takvim.

## Tutarlılık nasıl hesaplanıyor? (önemli)

Veri kronolojik olarak üçe bölünür: **%60 eğitim** (kurallar burada aranır), **%20 doğrulama** (elenir) ve
**%20 test** (hiç dokunulmamış son dönem). Raporlanan tutarlılık **her zaman test dönemindeki isabettir.**

- Kombinasyon arama: 5 koşula kadar beam search. Aynı indikatörün iki durumu aynı kombinasyonda kullanılmaz.
- Gün sonu hedefinde aynı günün mumları aynı sonucu paylaşır. Bu yüzden her günün yalnızca **ilk** sinyali sayılır
  ve istatistik "bağımsız gün" üzerinden hesaplanır. Böylece şişirilmiş oranların önüne geçilir.
- ML modelleri (Gradient Boosting, Lojistik Regresyon) walk-forward ile eğitilir. Güven eşiği önceki dilimlerde seçilir,
  son dilimde ölçülür.
- Saf rastgele fiyat verisiyle yapılan testte sistem **sıfır** kural buldu. Yani geleceğe bakış (sızıntı) yok ve
  rastgelelikten "sahte formasyon" üretmiyor.
- **Dürüst uyarı:** kurallar yine de "testte tutanlar" diye seçildiği için test oranları bir miktar iyimserdir. Bunun ölçüsü
  `python -m btc_tahmin sahte` komutudur: hedefler koşullara göre tam gün kaydırılır ve madencilik tekrarlanır; karışık veride
  çıkan kural sayısı, gerçek listede kaç kuralın şans olabileceğini gösterir. Asıl hakem canlı karnedir: 100+ sonuçlanmış
  sinyalden sonra canlı isabet ile beklenen arasındaki fark Veri durumu panelinde izlenir, 10 puanı aşarsa uyarı verir.
- **Veri bütünlüğü:** mum serisindeki boşluklar (Binance bakımı, indirme kesintisi) Veri durumu panelinde raporlanır;
  boşluk anlarında indikatörler bozulabilir.

> Gerçekçi beklenti: tek bir 15m mumun yönü büyük ölçüde gürültüdür. Sistem çoğu zaman **"tutarlı sinyal yok"** der.
> Bu bir hata değildir. %80-90 tutarlılık ancak nadir oluşan koşullarda görülür. `Test n` küçükse temkinli ol.
> Tutarlılık geçmişe aittir; piyasa rejimi değişirse düşebilir. Bu araç bir karar destek sistemidir, yatırım tavsiyesi değildir.

## Genel Piyasa Puanı ve kırımlar

`ayarlar/olaylar.json` dosyasındaki kırımlar (ör. *İran savaşı -10* → **Genel puan %90**) modellere **girmez**.
Bunlar sadece raporda ayrıca gösterilir. Böylece savaşın ne zaman biteceği belli değilken modelin istatistiği bozulmaz,
ama sen ortamın riskli olduğunu görürsün. Otomatik kırımlar da eklenir: aşırı korku veya açgözlülük, aşırı funding,
OI patlaması, yükselen stablecoin dominansı, olumsuz haber akışı, 24 saat içindeki FOMC/CPI ve hafta sonu.
"Kırım dahil long riski" de ayrı bir satırda, bilgi amaçlı gösterilir.

Takvime FOMC, CPI ve NFP gibi olayları UTC tarihleriyle ekle. Dosyadaki CPI/NFP tarihleri örnektir, doğrulaman gerekir.

## Ayarlar

`btc_tahmin/config.py`: semboller, geçmiş gün sayısı, en fazla koşul sayısı (5), minimum örnek sayıları,
tutarlılık seviyeleri (%90/85/80/75/70), gün sonu saat dilimi (TSİ).

## Test (ağ gerektirmez)

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests/test_birim.py   # birim testleri (saniyeler)
python -m pytest -q                       # hepsi: uçtan uca, sızıntı (rastgele veride 0 kural), karne (~2 dk)
```

Her push ve PR'da GitHub Actions aynı testleri Python 3.11 ve 3.12 ile çalıştırır (`.github/workflows/test.yml`).
