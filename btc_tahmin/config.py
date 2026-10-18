"""Genel ayarlar. Sana özel olanlar (kasa, işlem türü, Telegram) ayarlar/kullanici.json dosyasında."""
import json
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def _surum() -> str:
    """Çalışan kodun git sürümü (panoda gösterilir; güncelleme gelmiş mi anlamak için)."""
    import subprocess
    try:
        return subprocess.run(["git", "log", "-1", "--format=%h · %cd", "--date=format:%d.%m %H:%M"], cwd=KOK,
                              capture_output=True, text=True, timeout=5).stdout.strip() or "bilinmiyor"
    except (OSError, subprocess.SubprocessError):
        return "bilinmiyor"


SURUM = _surum()
VERI_DIR = KOK / "veri"          # indirilen mumlar ve önbellek
CIKTI_DIR = KOK / "cikti"        # rapor.html, rapor.json, kurallar.csv
AYAR_DIR = KOK / "ayarlar"       # olaylar.json (puan kırımları, takvim)

# İşlem çiftleri (Binance spot). Ana varlık ilk sıradadır.
SEMBOLLER = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
ANA_SEMBOL = "BTCUSDT"

# Desteklenen mum aralıkları. 10m Binance'te yok, 5m'den üretilir.
ARALIKLAR = ["15m", "10m", "5m", "30m", "1h", "4h"]   # 10m Binance'te yok, 5m'den üretilir
VARSAYILAN_ARALIK = "15m"

# Kaç günlük geçmiş indirilecek (15m * 540 gün ~ 52k mum)
GECMIS_GUN = 540

# "Gün sonu" hangi saat diliminde hesaplanır (Türkiye: UTC+3, yaz/kış farkı yok)
GUN_SONU_UTC_OFFSET_SAAT = 3
# Gün sonuna bundan az kalmışsa gün sonu tahmini yapılmaz (hedef anlamsızlaşır)
GUN_SONU_MIN_KALAN_SAAT = 1.0

# --- Kombinasyon madenciliği ---
MAX_KOSUL = 5                 # bir kombinasyonda en fazla kaç koşul
BEAM_GENISLIK = 250           # her seviyede saklanan en iyi aday sayısı
MIN_DESTEK_EGITIM = 40        # eğitim verisinde koşul en az kaç kez oluşmalı
MIN_DESTEK_TEST = 20          # test verisinde en az kaç kez oluşmalı
EGITIM_ORANI = 0.60           # kronolojik bölme: ilk %60 eğitim (kural arama)
DOGRULAMA_ORANI = 0.20        # sonraki %20 doğrulama (eleme), son %20 TEST (tutarlılık notu)
MIN_TUTARLILIK = 0.70         # %70 altı hiçbir sonuç raporlanmaz (ayarlar/kullanici.json 'min_tutarlilik' ile değişir, aşağıda)

# --- Derin tarama (ince eşikler, 3-7 koşul, çok mumlu hedefler) ---
DERIN_MIN_TUTARLILIK = 0.85   # bu taramada sadece %85 ve üstü gösterilir
DERIN_MIN_KOSUL = 3
DERIN_MAX_KOSUL = 7
DERIN_BEAM = 300
DERIN_ESIKLER = (30, 10, 15)  # birbirinden bağımsız oluşum sayısı: eğitim, doğrulama, test için en az
ILERI_MUMLAR = [2, 3, 4, 8]   # "N mum sonra fiyat yukarıda/aşağıda"
SERI_MUMLAR = [2, 3]          # "sonraki N mumun hepsi yeşil/kırmızı"
# (hedef sütunu, blok = bağımsızlık aralığı (mum), denenecek yönler)
DERIN_HEDEFLER = (
    [("sonraki_yesil", 1, (1, 0))]
    + [(f"ileri_{n}", n, (1, 0)) for n in ILERI_MUMLAR]
    + [(f"seri_{n}_{r}", n, (1,)) for n in SERI_MUMLAR for r in ("yesil", "kirmizi")]
)

# Geriye dönük kontrol: bu kadar dakika önce sinyale göre işlem açılsaydı şimdi ne olurdu?
GERIYE_DAKIKALAR = [15, 30, 45, 60]
GERIYE_MAX_MUM = 12
# Sinyal zaman çizelgesi (sinyaller.html): son kaç mum için sinyal ve çıkış hesaplanır (15m x 96 = 24 saat)
CIZELGE_MUM = 96

# Tutarlılık seviyeleri (Risk-A, Risk-B ...); eşik düşürülürse alt seviyeler de eklenir (aşağıda)
TUTARLILIK_SEVIYELERI = [0.90, 0.85, 0.80, 0.75, 0.70]

# --- Dış veri kaynakları ---
BINANCE_SPOT = ["https://api.binance.com", "https://data-api.binance.vision"]
BINANCE_FUTURES = "https://fapi.binance.com"
COINGECKO = "https://api.coingecko.com/api/v3"
FEAR_GREED = "https://api.alternative.me/fng/?limit=30"
HABER_RSS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://cryptoslate.com/feed/",
    "https://www.theblock.co/rss.xml",
]
HTTP_TIMEOUT = 20

# --- Kullanıcı ayarları (ayarlar/kullanici.json; yoksa kullanici.ornek.json'daki varsayılanlar) ---
def _kullanici() -> dict:
    for ad in ("kullanici.json", "kullanici.ornek.json"):
        f = AYAR_DIR / ad
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
    return {}


KULLANICI = _kullanici()
# İstersen ayarlar/kullanici.json'a "semboller": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT"] yazarak coin ekle
SEMBOLLER = [x.upper() for x in KULLANICI.get("semboller", SEMBOLLER)]

# Gösterme eşiği: bunun altında tutarlılıkta hiçbir kural/model sinyal vermez. 15m mumda tek mum yönü zor tahmin
# edildiği için %70 çoğu zaman "sinyal yok" demektir; 0.60-0.65 daha sık ama daha zayıf sinyal verir. Wilson ağırlığı
# sayesinde zayıf kaynaklar oylamada az söz hakkı alır. Değişince kurallar yeniden aranır (önbellek eşiğe bağlı).
MIN_TUTARLILIK = min(0.95, max(0.55, float(KULLANICI.get("min_tutarlilik", MIN_TUTARLILIK))))
TUTARLILIK_SEVIYELERI = [x for x in (0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55) if x >= MIN_TUTARLILIK - 1e-9]
# Eğilim: %MIN_TUTARLILIK altında kalsa bile modellerin o anki yönü; |olasılık - 0,5| bunu aşarsa gösterilir (düşük güven)
EGILIM_MARJI = float(KULLANICI.get("egilim_marji", 0.05))

# İşlem maliyeti: giriş + çıkış toplam yüzde (komisyon + kayma).
# vadeli: taker %0,05 x 2 + kayma ~%0,04 = %0,14 · spot: %0,10 x 2 + kayma ~%0,04 = %0,24
ISLEM_TURU = KULLANICI.get("islem_turu", "vadeli")
ISLEM_MALIYETI_YUZDE = {"vadeli": 0.14, "spot": 0.24, **KULLANICI.get("islem_maliyeti_yuzde", {})}
# Vadeli işlemde pozisyon açık kaldığı her 8 saat için ödenen funding (varsayılan oran %0,01). Uzun süreli (gün sonu, 8 mum)
# hedeflerde net kazanca maliyet olarak eklenir; spotta yoktur.
FUNDING_8S_YUZDE = float(KULLANICI.get("funding_8s_yuzde", 0.01)) if ISLEM_TURU == "vadeli" else 0.0
# Komisyon sonrası test döneminde zarar ettiren kurallar: False = gösterilir ama "KOMİSYONA YENİLİYOR" diye işaretlenir,
# True = hiç gösterilmez. 15m gibi kısa mumlarda hareketler küçük olduğu için True çoğu kuralı siler.
NET_ZARARLI_KURALLARI_ELE = bool(KULLANICI.get("net_zararli_kurallari_ele", False))

# Kural yaşlanması: son N oluşumdaki isabet, test tutarlılığından bu kadar düşükse uyar
YASLANMA_PENCERE = 20
YASLANMA_FARK = 0.15

# Kasa simülasyonu
SIM_BASLANGIC_KASA = float(KULLANICI.get("kasa_usd", 1000))
SIM_ISLEM_ORANI = 1.0              # her işlemde kasanın tamamı, kaldıraçsız

# Pozisyon önerisi
KASA_USD = float(KULLANICI.get("kasa_usd", 1000))
ISLEM_BASI_RISK_YUZDE = float(KULLANICI.get("islem_basi_risk_yuzde", 1.0))
MAX_KALDIRAC = float(KULLANICI.get("max_kaldirac", 3))

# Telegram bildirimi
TELEGRAM = {"token": "", "chat_id": "", "min_tutarlilik": 0.80, **KULLANICI.get("telegram", {})}

# Canlı karne: canlı isabeti bunun altına düşen kural (en az N canlı sinyalde) emekliye ayrılır
KARNE_MIN_SINYAL = 10
KARNE_EMEKLI_ORAN = 0.55
