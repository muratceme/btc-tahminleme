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
| `python -m btc_tahmin canli --ac` | **Önerilen.** Her 15m mumda yeniler, panoyu **http://localhost:8000** adresinde yayınlar. Aynı Wi-Fi'daki telefondan terminalde yazan `http://192.168.x.x:8000` adresiyle açılır |
| `python -m btc_tahmin izle --dakika 15 --ac` | Her 15m mum kapanışında otomatik yeniler, pano dakikada bir tazelenir |
| `python -m btc_tahmin ozet` | Son raporu terminalde tekrar gösterir |

Kısa yollar: Windows'ta `calistir.bat`, macOS/Linux'ta `./calistir.sh`. İkisi de `canli` modunu başlatır.

**Telefondan bakmak:** Telefon ile bilgisayar aynı Wi-Fi'da olmalı. Terminalde yazan `TELEFONDAN` adresini telefonun
tarayıcısına yaz. Windows "erişime izin ver" diye sorarsa **Özel ağlar** kutusunu işaretleyip izin ver.
Bilgisayar açık ve pencere açık olduğu sürece pano güncel kalır.

**Claude Code ile:** repo klasöründe `claude` açıp `/btc-rapor` yaz. Rapor üretilir ve Wall Street brifingi
formatında özetlenir. Sürekli takip için: `/loop 15m /btc-rapor hizli`. Kırım eklemek için:
`/btc-rapor kirim: Fed belirsizliği 5`.

İlk çalıştırma yaklaşık 540 günlük veri indirir ve kural madenciliği yapar. Bu birkaç dakika sürebilir.
Sonraki çalıştırmalar sadece yeni mumları indirir.

## Çıktılar (`cikti/`)

- `rapor.html`: Bloomberg terminali tarzı koyu pano (genel puan, dominanslar, F&G, vadeli, her coin için risk tablosu, aktif kombinasyonlar, haberler)
- `rapor.json`: tüm sayılar (başka araçlara bağlamak için)
- `kurallar_BTCUSDT_15m.csv`: bulunan tüm kombinasyon kuralları ve test istatistikleri

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
taker alış/satış, haber başlıkları (CoinDesk, Cointelegraph, Decrypt, anahtar kelime skoru), ekonomik takvim.

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
python -m tests.sentetik_test
```
