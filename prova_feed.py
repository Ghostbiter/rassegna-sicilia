# PROVVISORIO: controlla i feed candidati per lo scenario internazionale (non pubblica niente)
import urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import mondo
CANDIDATI = [
 "https://www.ilpost.it/mondo/feed/",
 "https://www.ilfattoquotidiano.it/mondo/feed/", "https://www.ilfattoquotidiano.it/category/mondo/feed/",
 "https://www.ilfattoquotidiano.it/feed/",
 "https://xml2.corriereobjects.it/rss/esteri.xml", "https://xml2.corriereobjects.it/rss/homepage.xml",
 "https://www.corriere.it/rss/esteri.xml",
 "https://www.tgcom24.mediaset.it/rss/mondo.xml",
 "https://www.ilmessaggero.it/rss/mondo.xml",
 "https://it.euronews.com/rss?format=mrss&level=theme&name=news", "https://it.euronews.com/rss",
 "https://www.agenzianova.com/feed/",
 "https://www.avvenire.it/rss/mondo", "https://www.avvenire.it/mondo/rss",
 "https://www.lastampa.it/rss/esteri.xml", "https://www.lastampa.it/esteri/rss",
 "https://tg24.sky.it/rss/tg24_mondo.xml", "https://tg24.sky.it/mondo/rss",
 "https://www.adnkronos.com/RSS_Esteri.xml", "https://www.adnkronos.com/rss/esteri",
 "https://ilmanifesto.it/feed", "https://ilmanifesto.it/sezioni/internazionale/feed",
 "https://www.ispionline.it/it/feed", "https://www.limesonline.com/rss",
 "https://www.open.online/esteri/feed/", "https://www.fanpage.it/esteri/feed/",
 "https://www.huffingtonpost.it/esteri/rss", "https://www.ilfoglio.it/esteri/rss",
 "https://www.editorialedomani.it/rss/mondo", "https://www.ilsole24ore.com/rss/mondo.xml",
 "https://www.rainews.it/rss/esteri", "https://www.agi.it/estero/rss",
]
ATOM = "{http://www.w3.org/2005/Atom}"

def prova(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=mondo.UA), timeout=20)
        b = r.read(); tipo = r.headers.get("Content-Type", "")
    except Exception as e:
        return f"ERR   {url}  {str(e)[:60]}"
    try:
        root = ET.fromstring(b.lstrip())
    except Exception:
        return f"XML?  {url}  {len(b)}B {tipo[:25]} inizio={b[:60]!r}"
    voci = list(root.iter("item")) + list(root.iter(ATOM + "entry"))
    date = [d for d in (mondo.data_di(v.findtext("pubDate") or v.findtext(ATOM + "updated") or v.findtext(ATOM + "published"))
                        for v in voci) if d]
    ieri = datetime.now(timezone.utc) - timedelta(hours=24)
    canale = mondo.pulisci(root.findtext("channel/title") or root.findtext(ATOM + "title") or "")
    primo = mondo.pulisci(voci[0].findtext("title") or voci[0].findtext(ATOM + "title") or "") if voci else ""
    return (f"OK    {url}  voci={len(voci)} ultime24h={sum(d >= ieri for d in date)} "
            f"più_recente={max(date).isoformat(timespec='minutes') if date else '-'} canale='{canale[:40]}' primo='{primo[:60]}'")

with ThreadPoolExecutor(12) as ex:
    for riga in ex.map(prova, CANDIDATI): print(riga)
