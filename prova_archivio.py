# PROVVISORIO: quanti feed dello scenario internazionale ha salvato la Wayback Machine, giorno per giorno
import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import mondo

GIORNI = ["2026-09-%02d" % d for d in range(21, 30)]

def cdx(url):
    q = urllib.parse.urlencode({"url": url, "from": "20260921", "to": "20260929", "output": "json",
                                "fl": "timestamp,statuscode", "filter": "statuscode:200"})
    for tentativo in range(3):
        try:
            r = urllib.request.urlopen("https://web.archive.org/cdx/search/cdx?" + q, timeout=40).read()
            righe = json.loads(r or b"[]")[1:]
            return [t for t, _ in righe]
        except Exception as e:
            errore = str(e)[:50]; time.sleep(3)
    return errore

def prova(voce):
    nome, url, lingua, stampa = voce
    if nome.startswith("GN"): return nome, "google news: non archiviabile", None
    ts = cdx(url)
    if isinstance(ts, str): return nome, "ERRORE " + ts, None
    per_giorno = Counter(f"{t[:4]}-{t[4:6]}-{t[6:8]}" for t in ts)
    # una copia: si legge davvero? quante voci e che date copre?
    esempio = None
    if ts:
        t = ts[len(ts) // 2]
        try:
            b = urllib.request.urlopen(f"https://web.archive.org/web/{t}id_/{url}", timeout=40).read()
            root = ET.fromstring(b.lstrip())
            voci = list(root.iter("item")) + list(root.iter(mondo.ATOM + "entry"))
            date = [d for d in (mondo.data_di(v.findtext("pubDate") or v.findtext(mondo.ATOM + "updated")) for v in voci) if d]
            esempio = f"copia {t}: {len(voci)} voci, dal {min(date):%d/%m %H:%M} al {max(date):%d/%m %H:%M}" if date else f"copia {t}: {len(voci)} voci senza date"
        except Exception as e:
            esempio = f"copia {t}: non leggibile ({str(e)[:40]})"
    return nome, " ".join(f"{g[8:]}:{per_giorno.get(g, 0):>3}" for g in GIORNI), esempio

with ThreadPoolExecutor(6) as ex:
    for nome, riga, esempio in ex.map(prova, mondo.FEED):
        print(f"{nome:<26} {riga}")
        if esempio: print(f"{'':<26} {esempio}")
