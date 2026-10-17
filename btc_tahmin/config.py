"""Genel ayarlar. Değiştirmek istediğin her şey burada."""
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI_DIR = KOK / "veri"          # indirilen mumlar ve önbellek
CIKTI_DIR = KOK / "cikti"        # rapor.html, rapor.json, kurallar.csv
AYAR_DIR = KOK / "ayarlar"       # olaylar.json (puan kırımları, takvim)

# İşlem çiftleri (Binance spot). Ana varlık ilk sıradadır.
SEMBOLLER = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
ANA_SEMBOL = "BTCUSDT"

# Desteklenen mum aralıkları. 10m Binance'te yok, 5m'den üretilir.
ARALIKLAR = ["15m", "10m"]
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
MIN_TUTARLILIK = 0.70         # %70 altı hiçbir sonuç raporlanmaz

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

# Tutarlılık seviyeleri (Risk-A, Risk-B ...)
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
