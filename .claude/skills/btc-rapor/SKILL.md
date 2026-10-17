---
name: btc-rapor
description: BTC/ETH/XRP gün sonu risk raporunu üretir ve Wall Street sabah brifingi tarzında Türkçe özetler. "rapor", "risk ne", "btc durum", "piyasa nasıl", "long açayım mı", "kırım ekle" gibi isteklerde kullan. Argüman örnekleri: "10m", "hizli", "BTC ETH", "kirim: Fed belirsizliği 5".
---

# BTC / ETH / XRP Risk Brifingi

Bu repo, 15m (veya 10m) mumlarda yüzlerce indikatör/formasyon kombinasyonunu tarar,
gün sonu risk oranlarını **tutarlılık** (hiç görülmemiş test dönemindeki isabet) ile birlikte üretir.

## 1. Raporu üret

Argümanlara göre komutu kur (repo kökünde çalıştır):

```bash
python -m btc_tahmin rapor [--aralik 10m] [--hizli] [--coin BTC ETH]
```

- `hizli` geçerse `--hizli` ekle (24 saatten yeni kural önbelleği kullanılır, ~1 dk).
- İlk çalıştırma veriyi indirir ve kural madenciliği yapar; birkaç dakika sürebilir. Zaman aşımını 15 dk ver.
- `ModuleNotFoundError` olursa: `pip install -r requirements.txt` çalıştırıp tekrar dene.
- Ağ hatası olursa hangi kaynağın düştüğünü söyle; rapor yine de kısmi üretilir (`baglam.hatalar`).

## 2. Puan kırımı ekleme/çıkarma (argümanda "kirim" varsa)

`ayarlar/olaylar.json` içindeki `genel_puan_kirimlari` listesini düzenle:
`{"ad": "...", "kirim_yuzde": 5, "aktif": true, "not": "..."}`. Bir olayı kapatmak için `aktif: false`.
Takvim olayı (FOMC, CPI vb.) eklemek için `takvim` listesine UTC tarihli kayıt ekle. Sonra raporu `--hizli` ile yeniden üret.

## 3. Brifingi yaz

`cikti/rapor.json` dosyasını oku ve kullanıcıya **Türkçe, kısa, Wall Street sabah notu** formatında sun:

1. **Başlık satırı**: tarih/saat (TSİ), Genel Piyasa Puanı ve kırım kalemleri (manuel olanları ayrıca belirt; bunlar modele girmez, sadece bilgi).
2. **Makro panel**: dominanslar (BTC.D, ETH.D, XRP.D, USDT.D, USDC.D, stable toplam) ve 24s/7g değişimleri, `dominans.yorum` maddeleri, Korku/Açgözlülük, funding / OI / long-short, yaklaşan olaylar.
3. **Her coin için** (BTC, ETH, XRP):
   - Fiyat, 24s değişim.
   - `risk.ozet.long_risk` / `short_risk` → "GÜN SONU LONG RİSKİ %X". Yoksa "tutarlı sinyal yok" de ve ham model tahminini *düşük güvenli* olarak ver.
   - `kirimli_long_risk`: puan kırımı dahil risk (ayrı satır, "bilgi amaçlı").
   - Risk tablosu: `risk.satirlar` → markdown tablo: `Etiket | Tutarlılık | Test n | Durum (SİNYAL/bekle) | Long risk | Short risk | Kaynak`. En fazla 10 satır.
   - Max düşüş sınırları (`ozet.max_dusus`): stop seviyesi önerisi olarak yorumla.
   - **Sonraki mum**: `sonraki_mum.aktif_kurallar` varsa en iyi 5'i şu formatta yaz:
     "RSI 30-45 + MACD negatif-artan + Supertrend boğa + ... iken sonraki mum testte %78 YEŞİL geldi (n=46)".
   - **Derin tarama** (`derin.aktif`): %85+ tutarlılıklı, 3-7 koşullu kurallar. Varsa hedefi (ör. `ileri_3` = 3 mum sonra fiyat, `seri_3_yesil` = sonraki 3 mumun hepsi yeşil) ve koşulları düz Türkçe yaz; grafik için `cikti/grafik.html?s=<SEMBOL>_<aralik>&k=<id>` adresini ver.
   - **Para tarafı:** kurallardaki `performans.test.ort_net` (komisyon sonrası işlem başı net %) ve `kar_faktoru`; `ZAYIFLIYOR` (`performans.yaslaniyor`) olanları belirt. `pozisyon` doluysa giriş/stop/hedef/pozisyon büyüklüğünü yaz. `simulasyon.derin` varsa 1.000$'ın test dönemindeki sonucunu tek satırda ver (iyimser olduğunu belirt).
4. **Canlı karne** (`karne`): genel ve son 7 gün canlı isabeti, beklenenle karşılaştır. Canlı isabet beklenenin çok altındaysa bunu açıkça uyar.
5. **Makro** (`baglam.makro`, `baglam.etf`, `baglam.opsiyon`, `baglam.takvim_oto`): Nasdaq/DXY değişimi, ETF son gün akışı, put/call ve max pain, 48 saatteki önemli veriler.
6. **Sonuç kutusu**: her coin için tek satır karar özeti — "Long için uygun / temkinli / uzak dur" (long risk <40 uygun, 40-60 temkinli, >60 uzak dur; test n küçükse bir kademe temkinli ol).
7. Sonda HTML panonun yolunu ver: `cikti/rapor.html` (tarayıcıda açılabilir).

Kurallar:
- Tutarlılığı %70 altında olan hiçbir şeyi risk oranı gibi sunma.
- Tutarlılığın geçmiş test dönemine ait olduğunu, garanti olmadığını tek cümleyle hatırlat. Yatırım tavsiyesi verme; kararı kullanıcı verir.
- Sayıları uydurma; sadece rapor.json'daki değerleri kullan.

## Sürekli izleme

Kullanıcı sürekli takip isterse iki seçenek öner:
- Terminalde: `python -m btc_tahmin canli --ac` (her mum kapanışında yeniler, pano http://localhost:8000 adresinde; aynı Wi-Fi'daki telefondan terminalde yazan IP adresiyle açılır).
- Claude Code içinde: `/loop 15m /btc-rapor hizli`.
