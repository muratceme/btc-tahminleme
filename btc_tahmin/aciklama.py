"""Koşul adlarını insan diline çevirir: Türkçe etiket, eğilim ve açıklama.

Eğilim kodları: "boga" (yükseliş lehine), "ayi" (düşüş lehine), "asiri" (aşırı bölge, dönüş
olabilir), "notr". Bunlar sadece anlık durumu tarif eder; tahmini modeller ve kurallar yapar.
"""
from __future__ import annotations

import re

# aile -> (grup, okunur ad, ne ölçer, {durum: (etiket, eğilim)})
AILELER: dict[str, tuple[str, str, str, dict[str, tuple[str, str]]]] = {
    "RSI": ("Momentum", "RSI (14)", "Son 14 mumdaki yükseliş ve düşüşlerin gücünü 0-100 arasında ölçer. 70 üstü aşırı alım, 30 altı aşırı satım sayılır.", {
        "<30": ("RSI 30'un altında (aşırı satım)", "asiri"), "30-45": ("RSI 30-45 (zayıf)", "ayi"),
        "45-55": ("RSI 45-55 (nötr)", "notr"), "55-70": ("RSI 55-70 (güçlü)", "boga"), ">70": ("RSI 70'in üstünde (aşırı alım)", "asiri")}),
    "RSI_YON": ("Momentum", "RSI yönü", "RSI son 2 mumda yükseliyor mu düşüyor mu?", {
        "yukari": ("RSI yükseliyor", "boga"), "asagi": ("RSI düşüyor", "ayi")}),
    "STOCH": ("Momentum", "Stochastic", "Kapanışın son 14 mumun aralığında nerede olduğunu gösterir. 80 üstü tepe, 20 altı dip bölgesi.", {
        "<20": ("Stochastic dipte (<20)", "asiri"), "20-80": ("Stochastic orta bölgede", "notr"), ">80": ("Stochastic tepede (>80)", "asiri")}),
    "STOCH_KESISIM": ("Momentum", "Stochastic kesişimi", "%K çizgisinin %D çizgisini kesmesi. Kısa vadeli dönüş sinyali.", {
        "yukari": ("Stochastic yukarı kesti", "boga"), "asagi": ("Stochastic aşağı kesti", "ayi")}),
    "STOCHRSI": ("Momentum", "Stochastic RSI", "RSI'ın kendi aralığındaki konumu. Çok hızlı tepki veren bir aşırı alım/satım göstergesi.", {
        "<20": ("StochRSI dipte (<20)", "asiri"), "20-80": ("StochRSI orta bölgede", "notr"), ">80": ("StochRSI tepede (>80)", "asiri")}),
    "MACD_HIST": ("Momentum", "MACD histogramı", "Kısa (12) ve uzun (26) ortalamanın farkının sinyal çizgisine uzaklığı. Momentumun hızlanıp yavaşladığını gösterir.", {
        "pozitif_artan": ("MACD pozitif ve güçleniyor", "boga"), "pozitif_azalan": ("MACD pozitif ama zayıflıyor", "notr"),
        "negatif_artan": ("MACD negatif ama toparlanıyor", "notr"), "negatif_azalan": ("MACD negatif ve derinleşiyor", "ayi")}),
    "MACD_KESISIM": ("Momentum", "MACD kesişimi", "MACD çizgisinin sinyal çizgisini kesmesi. Klasik al/sat tetikleyicisi.", {
        "yukari": ("MACD yukarı kesti (al)", "boga"), "asagi": ("MACD aşağı kesti (sat)", "ayi")}),
    "MACD_SIFIR": ("Trend", "MACD sıfır çizgisi", "MACD sıfırın üstündeyse kısa ortalama uzun ortalamanın üstündedir, yani trend yukarıdır.", {
        "ustunde": ("MACD sıfırın üstünde", "boga"), "altinda": ("MACD sıfırın altında", "ayi")}),
    "EMA9_21": ("Trend", "EMA 9/21", "Çok kısa vadeli trend: 9 mumluk ortalama 21 mumluğun üstünde mi?", {
        "boga": ("EMA9 > EMA21 (kısa trend yukarı)", "boga"), "ayi": ("EMA9 < EMA21 (kısa trend aşağı)", "ayi")}),
    "EMA21_50": ("Trend", "EMA 21/50", "Kısa-orta vadeli trend.", {
        "boga": ("EMA21 > EMA50 (orta trend yukarı)", "boga"), "ayi": ("EMA21 < EMA50 (orta trend aşağı)", "ayi")}),
    "FIYAT_EMA200": ("Trend", "Fiyat / EMA200", "200 mumluk ortalama ana trend çizgisidir. Fiyat üstündeyse genel yapı yukarıdır.", {
        "ustunde": ("Fiyat EMA200'ün üstünde", "boga"), "altinda": ("Fiyat EMA200'ün altında", "ayi")}),
    "EMA_DIZILIM": ("Trend", "EMA dizilimi", "9>21>50>200 sıralaması tam boğa, tersi tam ayı dizilimidir. En güçlü trend teyitlerinden biridir.", {
        "tam_boga": ("EMA'lar tam boğa diziliminde", "boga"), "tam_ayi": ("EMA'lar tam ayı diziliminde", "ayi")}),
    "BOLLINGER": ("Volatilite", "Bollinger bantları", "20 mumluk ortalamanın ±2 standart sapmalık bandı. Fiyatın bant içindeki konumu (%B).", {
        "alt_bant_disi": ("Fiyat alt Bollinger bandının dışında", "asiri"), "alt_bolge": ("Fiyat alt banda yakın", "ayi"),
        "orta": ("Fiyat bandın ortasında", "notr"), "ust_bolge": ("Fiyat üst banda yakın", "boga"), "ust_bant_disi": ("Fiyat üst Bollinger bandının dışında", "asiri")}),
    "BB_SIKISMA": ("Volatilite", "Bollinger sıkışması", "Bantlar son 120 mumun en dar %15'inde. Sert bir hareket öncesi sessizlik olabilir.", {
        "var": ("Bollinger sıkışması var (patlama yakın olabilir)", "notr")}),
    "ADX": ("Trend", "ADX trend gücü", "Trendin yönünü değil gücünü ölçer. 20 altı yatay piyasa, 30 üstü güçlü trend.", {
        "zayif_trend<20": ("ADX < 20 (yatay piyasa)", "notr"), "20-30": ("ADX 20-30 (trend oluşuyor)", "notr"), "guclu_trend>30": ("ADX > 30 (güçlü trend)", "notr")}),
    "DI": ("Trend", "DI+ / DI-", "Yön göstergesi: alıcıların mı satıcıların mı baskın olduğu.", {
        "boga": ("DI+ > DI- (alıcılar baskın)", "boga"), "ayi": ("DI- > DI+ (satıcılar baskın)", "ayi")}),
    "CCI": ("Momentum", "CCI", "Fiyatın ortalamasından ne kadar saptığını ölçer. ±100 dışı aşırı bölgedir.", {
        "<-100": ("CCI -100'ün altında", "asiri"), "-100..100": ("CCI normal aralıkta", "notr"), ">100": ("CCI +100'ün üstünde", "asiri")}),
    "MFI": ("Hacim", "MFI (para akışı)", "Hacimle ağırlıklandırılmış RSI. Paranın girip girmediğini gösterir.", {
        "<20": ("MFI < 20 (para çıkışı aşırı)", "asiri"), "20-80": ("MFI normal", "notr"), ">80": ("MFI > 80 (para girişi aşırı)", "asiri")}),
    "WILLIAMS_R": ("Momentum", "Williams %R", "Stochastic'e benzer. -20 üstü aşırı alım, -80 altı aşırı satım.", {
        "<-80": ("Williams %R aşırı satımda", "asiri"), "-80..-20": ("Williams %R normal", "notr"), ">-20": ("Williams %R aşırı alımda", "asiri")}),
    "SUPERTREND": ("Trend", "Supertrend", "ATR tabanlı trend takip göstergesi. Yön değiştirdiğinde trend dönmüş sayılır.", {
        "boga": ("Supertrend boğa", "boga"), "ayi": ("Supertrend ayı", "ayi")}),
    "ICHIMOKU": ("Trend", "Ichimoku bulutu", "Japon denge grafiği. Fiyat bulutun üstündeyse yükseliş, altındaysa düşüş bölgesindedir.", {
        "bulut_ustu": ("Fiyat Ichimoku bulutunun üstünde", "boga"), "bulut_alti": ("Fiyat Ichimoku bulutunun altında", "ayi"), "bulut_ici": ("Fiyat bulutun içinde (kararsız)", "notr")}),
    "TK": ("Trend", "Tenkan / Kijun", "Ichimoku'nun hızlı ve yavaş çizgileri. Klasik TK kesişimi.", {
        "boga": ("Tenkan > Kijun", "boga"), "ayi": ("Tenkan < Kijun", "ayi")}),
    "VWAP": ("Hacim", "Günlük VWAP", "Gün içi hacim ağırlıklı ortalama fiyat. Kurumsal alıcıların referans aldığı seviyedir.", {
        "ustunde": ("Fiyat VWAP'ın üstünde", "boga"), "altinda": ("Fiyat VWAP'ın altında", "ayi")}),
    "HACIM": ("Hacim", "Hacim seviyesi", "Son mumun hacmi, son 96 mumun ortalamasına göre ne kadar yüksek (z-skoru)?", {
        "dusuk": ("Hacim düşük", "notr"), "normal": ("Hacim normal", "notr"), "yuksek": ("Hacim yüksek", "notr"), "asiri": ("Hacim aşırı yüksek (olay var)", "asiri")}),
    "ALICI_BASKISI": ("Hacim", "Alıcı / satıcı baskısı", "Piyasa emriyle alanların hacimdeki payı (taker buy). %55 üstü alıcılar agresif demektir.", {
        "satici": ("Satıcılar agresif", "ayi"), "dengeli": ("Alıcı-satıcı dengeli", "notr"), "alici": ("Alıcılar agresif", "boga")}),
    "OBV": ("Hacim", "OBV eğimi", "Hacim kümülatif olarak yükseliş mumlarında mı birikiyor, düşüş mumlarında mı?", {
        "artan": ("OBV artıyor (hacim alımda)", "boga"), "azalan": ("OBV azalıyor (hacim satışta)", "ayi")}),
    "VOLATILITE": ("Volatilite", "Volatilite rejimi", "ATR'nin (ortalama mum boyu) tüm geçmişteki sıralaması.", {
        "dusuk": ("Volatilite düşük", "notr"), "orta": ("Volatilite orta", "notr"), "yuksek": ("Volatilite yüksek", "asiri")}),
    "MOMENTUM_4S": ("Momentum", "Son 4 saat getirisi", "Fiyatın son 16 mumda (15m'de 4 saat) yüzde değişimi.", {
        "sert_dusus": ("Son 4 saatte sert düşüş (<-1.5%)", "ayi"), "dusus": ("Son 4 saatte düşüş", "ayi"), "yatay": ("Son 4 saat yatay", "notr"),
        "yukselis": ("Son 4 saatte yükseliş", "boga"), "sert_yukselis": ("Son 4 saatte sert yükseliş (>1.5%)", "boga")}),
    "KELTNER": ("Volatilite", "Keltner kanalı", "EMA20 ± 2 ATR. Kanal dışına çıkış güçlü hareket ya da aşırılık demektir.", {
        "ust_disi": ("Fiyat Keltner üst kanalının dışında", "asiri"), "alt_disi": ("Fiyat Keltner alt kanalının dışında", "asiri")}),
    "SON_MUM": ("Fiyat hareketi", "Son mum", "Son kapanan mumun rengi.", {
        "yesil": ("Son mum yeşil", "boga"), "kirmizi": ("Son mum kırmızı", "ayi")}),
    "SEANS": ("Zaman", "Seans", "Hangi borsa seansındayız (UTC). Likidite ve volatilite seanslara göre değişir.", {
        "asya": ("Asya seansı (03:00-11:00 TSİ)", "notr"), "avrupa": ("Avrupa seansı (11:00-16:00 TSİ)", "notr"),
        "abd": ("ABD seansı (16:00-24:00 TSİ)", "notr"), "gec_abd": ("Geç ABD / kapanış (00:00-03:00 TSİ)", "notr")}),
    "HAFTA_SONU": ("Zaman", "Hafta sonu", "Hafta sonu kurumsal katılım ve likidite düşüktür.", {
        "evet": ("Hafta sonu", "notr")}),
}

# formasyon adı -> (etiket, eğilim, açıklama)
FORMASYONLAR: dict[str, tuple[str, str, str]] = {
    "DOJI": ("Doji", "notr", "Açılış ve kapanış neredeyse aynı. Kararsızlık, olası dönüş."),
    "CEKIC": ("Çekiç", "boga", "Düşüş sonrası uzun alt fitil. Alıcılar dipten topladı."),
    "TERS_CEKIC": ("Ters çekiç", "boga", "Düşüş sonrası uzun üst fitil. Alıcılar denedi; teyit gerekir."),
    "KAYAN_YILDIZ": ("Kayan yıldız", "ayi", "Yükseliş sonrası uzun üst fitil. Satıcılar tepeden bastırdı."),
    "ASILI_ADAM": ("Asılı adam", "ayi", "Yükseliş sonrası uzun alt fitil. Tepede zayıflık işareti."),
    "YUTAN_BOGA": ("Yutan boğa", "boga", "Yeşil mum önceki kırmızıyı tamamen yuttu. Güçlü dönüş sinyali."),
    "YUTAN_AYI": ("Yutan ayı", "ayi", "Kırmızı mum önceki yeşili tamamen yuttu. Güçlü düşüş sinyali."),
    "HARAMI_BOGA": ("Boğa harami", "boga", "Küçük yeşil mum önceki büyük kırmızının içinde. Satış yavaşlıyor."),
    "HARAMI_AYI": ("Ayı harami", "ayi", "Küçük kırmızı mum önceki büyük yeşilin içinde. Alım yavaşlıyor."),
    "SABAH_YILDIZI": ("Sabah yıldızı", "boga", "Kırmızı, küçük gövde, güçlü yeşil: 3 mumluk dip dönüşü."),
    "AKSAM_YILDIZI": ("Akşam yıldızı", "ayi", "Yeşil, küçük gövde, güçlü kırmızı: 3 mumluk tepe dönüşü."),
    "UC_BEYAZ_ASKER": ("Üç beyaz asker", "boga", "Art arda 3 güçlü yeşil mum. Kararlı alım."),
    "UC_KARA_KARGA": ("Üç kara karga", "ayi", "Art arda 3 güçlü kırmızı mum. Kararlı satış."),
    "MARUBOZU_BOGA": ("Boğa marubozu", "boga", "Fitilsiz büyük yeşil mum. Alıcılar baştan sona kontrolde."),
    "MARUBOZU_AYI": ("Ayı marubozu", "ayi", "Fitilsiz büyük kırmızı mum. Satıcılar baştan sona kontrolde."),
    "IC_MUM": ("İç mum (inside bar)", "notr", "Mum öncekinin aralığında kaldı. Sıkışma, kırılım beklenir."),
    "DIS_MUM": ("Dış mum (outside bar)", "notr", "Mum öncekinin hem üstüne hem altına taştı. Volatilite artışı."),
    "PIN_BAR_BOGA": ("Boğa pin bar", "boga", "Aralığın 2/3'ü alt fitil. Aşağıdan sert ret."),
    "PIN_BAR_AYI": ("Ayı pin bar", "ayi", "Aralığın 2/3'ü üst fitil. Yukarıdan sert ret."),
    "CIMBIZ_DIP": ("Cımbız dip", "boga", "İki mum aynı dipten döndü. Destek teyidi."),
    "CIMBIZ_TEPE": ("Cımbız tepe", "ayi", "İki mum aynı tepeden döndü. Direnç teyidi."),
    "DELICI_HAT": ("Delici hat", "boga", "Boşlukla açılıp önceki kırmızının yarısını geçen yeşil mum."),
    "KARA_BULUT": ("Kara bulut", "ayi", "Boşlukla açılıp önceki yeşilin yarısının altına inen kırmızı mum."),
    "BUYUK_GOVDE": ("Büyük gövdeli mum", "notr", "Gövde, son 20 mumun ortalamasının 2,5 katı. Güçlü hareket."),
    "ARD_ARDA_3_YESIL": ("Art arda 3 yeşil", "boga", "Son üç mum yeşil."),
    "ARD_ARDA_3_KIRMIZI": ("Art arda 3 kırmızı", "ayi", "Son üç mum kırmızı."),
    "KIRILIM_YUKARI_20": ("20 mumluk zirve kırılımı", "boga", "Kapanış son 20 mumun en yükseğinin üstünde (Donchian kırılımı)."),
    "KIRILIM_ASAGI_20": ("20 mumluk dip kırılımı", "ayi", "Kapanış son 20 mumun en düşüğünün altında."),
    "IKILI_DIP": ("İkili dip", "boga", "İki yakın dip (%0,3 içinde) ve fiyat üstünde. W formasyonu."),
    "IKILI_TEPE": ("İkili tepe", "ayi", "İki yakın tepe ve fiyat altında. M formasyonu."),
    "YUKSELEN_DIPLER": ("Yükselen dipler ve tepeler", "boga", "Son iki pivotta hem dip hem tepe yükseldi. Yükselen trend yapısı."),
    "ALCALAN_TEPELER": ("Alçalan tepeler ve dipler", "ayi", "Son iki pivotta hem tepe hem dip alçaldı. Düşen trend yapısı."),
}

# Üst zaman dilimi ve diğer coin koşulları
_UZD = {
    "TREND": {"BOGA": ("trend yukarı (EMA21>EMA50)", "boga"), "AYI": ("trend aşağı (EMA21<EMA50)", "ayi")},
    "RSI": {"ASIRI_SATIM": ("RSI aşırı satımda (<35)", "asiri"), "ASIRI_ALIM": ("RSI aşırı alımda (>65)", "asiri")},
    "SUPERTREND": {"BOGA": ("Supertrend boğa", "boga")},
}
_COIN = {
    "1S:YUKARI": ("son 1 saatte yükseliyor", "boga"), "1S:ASAGI": ("son 1 saatte düşüyor", "ayi"),
    "GUC:BTCDEN_GUCLU": ("ana coinden güçlü", "notr"), "RSI:GT60": ("RSI > 60", "boga"), "RSI:LT40": ("RSI < 40", "ayi"),
    "BTC_PARITE:YUKSELIS": ("BTC paritesinde yükseliyor", "notr"),
}


def kosul_bilgisi(kosul: str) -> dict:
    """{"etiket", "egilim", "grup", "aciklama"} döner. Tanınmayan koşul ham haliyle gelir."""
    aile, _, durum = kosul.partition(":")
    if aile in AILELER:
        grup, ad, ne, durumlar = AILELER[aile]
        et, eg = durumlar.get(durum, (f"{ad}: {durum}", "notr"))
        return {"etiket": et, "egilim": eg, "grup": grup, "aciklama": ne}
    if aile.startswith("FORMASYON_"):
        f = aile.removeprefix("FORMASYON_")
        et, eg, ne = FORMASYONLAR.get(f, (f.replace("_", " ").title(), "notr", ""))
        return {"etiket": et, "egilim": eg, "grup": "Formasyon", "aciklama": ne}
    m = re.match(r"^(1S|4S)_(TREND|RSI|SUPERTREND)$", aile)
    if m:
        per = "1 saatlik" if m.group(1) == "1S" else "4 saatlik"
        et, eg = _UZD[m.group(2)].get(durum, (durum.lower(), "notr"))
        return {"etiket": f"{per} {et}", "egilim": eg, "grup": "Üst zaman dilimi",
                "aciklama": f"Aynı coinin {per} grafiğindeki durum. Büyük resmi gösterir."}
    m = re.match(r"^(BTC|ETH|XRP)_(.+)$", aile)
    if m:
        anahtar = f"{m.group(2)}:{durum}"
        et, eg = _COIN.get(anahtar, (anahtar.lower(), "notr"))
        return {"etiket": f"{m.group(1)} {et}", "egilim": eg, "grup": "Diğer coinler",
                "aciklama": "Diğer büyük coinlerin hareketi. Kripto piyasası genelde birlikte hareket eder."}
    return {"etiket": kosul, "egilim": "notr", "grup": "Diğer", "aciklama": ""}


GRUP_SIRASI = ["Trend", "Momentum", "Hacim", "Volatilite", "Formasyon", "Fiyat hareketi",
               "Üst zaman dilimi", "Diğer coinler", "Zaman", "Diğer"]
