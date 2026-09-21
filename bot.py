#!/usr/bin/env python3
"""Rassegna Sicilia: raccoglie le notizie da testate siciliane + Google News,
le classifica per provincia e argomento, elimina i duplicati (tiene la testata maggiore)
e salva docs/data/AAAA-MM-GG.json per il sito. Solo libreria standard."""
import time, threading, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET, html, re, json, os, sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data")

PROVINCE = {
 "Palermo": ["Palermo","Bagheria","Monreale","Carini","Partinico","Termini Imerese","Cefalù","Misilmeri","Corleone","Villabate","Isola delle Femmine","Petralia","Ustica","Capaci","Lampedusa"],
 "Catania": ["Catania","Acireale","Paternò","Misterbianco","Caltagirone","Adrano","Giarre","Riposto","Aci Castello","Aci Catena","Belpasso","Gravina di Catania","Bronte","Randazzo","Mascalucia","Palagonia","Scordia","Etna"],
 "Messina": ["Messina","Barcellona Pozzo di Gotto","Milazzo","Taormina","Patti","Capo d'Orlando","Sant'Agata di Militello","Giardini Naxos","Lipari","Eolie","Stromboli","Letojanni","Santa Teresa di Riva","Nebrodi"],
 "Siracusa": ["Siracusa","Augusta","Avola","Noto","Lentini","Pachino","Floridia","Priolo","Carlentini","Rosolini","Melilli","Palazzolo Acreide","Ortigia"],
 "Ragusa": ["Ragusa","Vittoria","Modica","Comiso","Scicli","Pozzallo","Ispica","Santa Croce Camerina","Marina di Ragusa","Acate"],
 "Trapani": ["Trapani","Marsala","Mazara del Vallo","Alcamo","Castelvetrano","Erice","Pantelleria","Favignana","Egadi","Salemi","Castellammare del Golfo","San Vito Lo Capo","Campobello di Mazara","Petrosino"],
 "Agrigento": ["Agrigento","Sciacca","Licata","Canicattì","Favara","Porto Empedocle","Ribera","Palma di Montechiaro","Menfi","Lampedusa e Linosa","Realmonte","Racalmuto"],
 "Caltanissetta": ["Caltanissetta","Gela","Niscemi","San Cataldo","Mazzarino","Riesi","Mussomeli","Butera"],
 "Enna": ["Enna","Piazza Armerina","Nicosia","Leonforte","Troina","Barrafranca","Agira","Pergusa","Regalbuto"],
}
ARGOMENTI = {
 "Cronaca": ["arrest","carabinier","polizia","incidente","morto","morta","omicidio","rapina","furto","indagin","procura","sequestr","mafia","droga","spaccio","denunciat","incendio","vigili del fuoco","tribunale","condann","processo","sparatoria","aggression","violenz","truffa","blitz","latitante","annegat","ferito","ferita","scomparso","giudice","pm "],
 "Politica": ["sindaco","regione","consiglio comunale","ars","schifani","assessore","giunta","elezioni","deputat","senator","partito","governo","ministro","fratelli d'italia","pd ","m5s","forza italia","lega","amministrative","opposizione","parlamento","decreto"],
 "Economia e lavoro": ["lavoro","lavorator","sindacat","impres","aziend","economia","euro","fondi","pnrr","occupazion","sciopero","precari","bando","investiment","porto","turismo","agricoltur","pesca","commercio","bilancio","finanziament","stipendi","vendemmia"],
 "Sport": ["calcio","serie a","serie b","serie c","serie d","partita","campionato","allenatore","gol","palermo fc","rosanero","catania fc","rossazzurri","acr messina","trapani calcio","basket","volley","pallavolo","ciclismo","atleta","torneo","stadio","match","vittoria per","pareggio","sconfitta"],
 "Cultura e spettacoli": ["festival","teatro","mostra","concerto","cinema","film","libro","museo","musica","spettacolo","cultura","artista","archeolog","sagra","festa","evento","rassegna","premio","scrittore","attore","attrice"],
 "Ambiente e meteo": ["meteo","maltempo","allerta","pioggia","temporal","caldo","siccità","ambiente","rifiuti","discarica","mare","spiagge","inquinament","terremoto","scossa","vulcano","eruzione","etna","ingv","acqua","crisi idrica","clima"],
 "Sanità": ["ospedale","sanità","asp ","medic","pazient","pronto soccorso","salute","vaccin","infermier","malattia","chirurg","policlinico","118"],
 "Trasporti e infrastrutture": ["autostrada","strada","ponte sullo stretto","ponte","treno","ferrovi","aeroporto","volo","voli","traghett","caronte","anas","cantiere","viabilità","trasporti","autobus","ryanair","metropolitana"],
 "Scuola e università": ["scuola","studenti","università","unipa","unict","unime","docent","insegnant","liceo","istituto","ateneo","anno scolastico"],
}

# Priorità testate (più alto = testata maggiore): usata per scegliere tra duplicati
PRIORITA = {
 "ansa":100,"giornale di sicilia":95,"gds":95,"la sicilia":95,"repubblica":93,"corriere della sera":92,"rai":90,"tgr":90,
 "sky tg24":88,"il sole 24 ore":88,"la stampa":85,"il fatto quotidiano":84,"agi":84,"adnkronos":83,"tgcom24":82,
 "livesicilia":80,"quotidiano di sicilia":78,"qds":78,"gazzetta del sud":80,"blogsicilia":72,"il sicilia":70,"ilsicilia":70,
 "palermotoday":70,"cataniatoday":70,"messinatoday":70,"agrigentonotizie":68,"newsicilia":66,"strettoweb":66,"tempostretto":66,
 "tp24":64,"siracusanews":62,"ragusanews":62,"seguonews":60,"gazzettadelsud":80,"lasicilia":95,"catania today":70,"palermo today":70,
}
NOMI = {"lasicilia.it":"La Sicilia","gds.it":"Giornale di Sicilia","qds.it":"Quotidiano di Sicilia",
        "ansa.it":"ANSA","repubblica.it":"la Repubblica","corriere.it":"Corriere della Sera",
        "rainews.it":"Rai News","ilsicilia.it":"ilSicilia","livesicilia.it":"LiveSicilia",
        "blogsicilia.it":"BlogSicilia","newsicilia.it":"NewSicilia","tp24.it":"Tp24"}
def nome_testata(f):
    """Nomi puliti: da 'lasicilia.it' a 'La Sicilia'."""
    f = (f or "").strip()
    if f.lower() in NOMI: return NOMI[f.lower()]
    m = re.fullmatch(r"(?:www\.)?([a-z0-9-]+)\.(?:it|com|eu|net|org|tv|info)", f.lower())
    return m.group(1).replace("-", " ").title() if m else f

def priorita(fonte):
    f = fonte.lower()
    return max((v for k, v in PRIORITA.items() if k in f), default=30)

FEED = {
 "ANSA Sicilia":"https://www.ansa.it/sicilia/notizie/sicilia_rss.xml",
 "LiveSicilia":"https://livesicilia.it/feed/",
 "BlogSicilia":"https://www.blogsicilia.it/feed/",
 "ilSicilia":"https://www.ilsicilia.it/feed/",
 "NewSicilia":"https://www.newsicilia.it/feed/",
 "QdS":"https://qds.it/feed/",
 "PalermoToday":"https://www.palermotoday.it/rss",
 "CataniaToday":"https://www.cataniatoday.it/rss",
 "AgrigentoNotizie":"https://www.agrigentonotizie.it/rss",
 "SiracusaNews":"https://www.siracusanews.it/feed/",
 "RagusaNews":"https://www.ragusanews.com/feed/",
 "StrettoWeb":"https://www.strettoweb.com/feed/",
 "Tempostretto":"https://www.tempostretto.it/feed",
}
# Giornale di Sicilia: un feed per ogni provincia
for _p, _slug in [("Sicilia","sicilia"),("Palermo","palermo"),("Catania","catania"),("Messina","messina"),
                  ("Siracusa","siracusa"),("Ragusa","ragusa"),("Trapani","trapani"),("Agrigento","agrigento"),
                  ("Caltanissetta","caltanissetta"),("Enna","enna")]:
    FEED[f"Giornale di Sicilia|{_p}"] = f"https://feedpress.me/gds_hp_{_slug}"
# Testate senza feed proprio: le seguiamo con una ricerca mirata su Google News
SENZA_FEED = {"La Sicilia":"lasicilia.it", "Gazzetta del Sud":"gazzettadelsud.it"}
GQ = {p: " OR ".join(f'"{c}"' for c in ([p] + PROVINCE[p][1:4])) for p in PROVINCE}
GQ["Vittoria"] = '"Vittoria" Ragusa'
GQ["Sicilia"] = '"Sicilia" OR siciliano OR siciliana'
for p in ["Palermo","Catania","Messina"]:
    GQ[p + " città"] = f'"{p}"'
for _nome, _dominio in SENZA_FEED.items():
    GQ[f"sito {_dominio}"] = f"site:{_dominio}"
for k, q in GQ.items():
    FEED[f"GN {k}"] = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"({q}) when:1d", "hl":"it","gl":"IT","ceid":"IT:it"})

NS = {"media":"http://search.yahoo.com/mrss/","content":"http://purl.org/rss/1.0/modules/content/"}

def immagine(it):
    for tag in ("media:content","media:thumbnail"):
        for e in it.findall(tag, NS):
            if e.get("url") and (e.get("medium") in (None,"image") or tag.endswith("thumbnail")): return e.get("url")
    e = it.find("enclosure")
    if e is not None and "image" in (e.get("type") or "image"): return e.get("url")
    for t in ("content:encoded","description"):
        m = re.search(r'<img[^>]+src=["\']([^"\']+)', it.findtext(t, "", NS) or "")
        if m: return m.group(1)
    return None

def scarica(nome_url):
    nome, url = nome_url
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (RassegnaSiciliaBot)"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        print("ERR", nome, str(e)[:70]); return []
    k = nome[3:].replace(" città","")
    if "|" in nome:                      # es. "Giornale di Sicilia|Catania"
        nome, k = nome.split("|")
    hint = k if k in PROVINCE else ("Ragusa" if k == "Vittoria" else None)
    out = []
    for it in root.iter("item"):
        titolo = html.unescape((it.findtext("title") or "").strip())
        fonte = nome
        if nome.startswith("GN"):
            fonte = (it.findtext("source") or "").strip()
            if " - " in titolo: titolo, f2 = titolo.rsplit(" - ", 1); fonte = fonte or f2
        try: data = parsedate_to_datetime(it.findtext("pubDate") or "")
        except Exception: continue
        if not data.tzinfo: data = data.replace(tzinfo=timezone.utc)
        desc = "" if nome.startswith("GN") else re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",html.unescape(it.findtext("description") or ""))).strip()
        out.append({"titolo":titolo,"link":(it.findtext("link") or "").strip(),"fonte":fonte,
                    "data":data.astimezone(ROMA).isoformat(timespec="minutes"),
                    "desc":desc[:220],"img":immagine(it),"_hint":hint})
    print("ok ", nome, len(out)); return out

def trova(testo, diz, default):
    t = " " + testo.lower() + " "
    punti = {k: sum(len(re.findall(r"\b" + re.escape(w.lower()), t)) for w in v) for k, v in diz.items()}
    k = max(punti, key=punti.get)
    return k if punti[k] else default

def parole(t): return set(w for w in re.findall(r"\w+", t.lower()) if len(w) > 3)

def ident(titolo):
    return hashlib.sha1(re.sub(r"\W+","",titolo.lower()).encode()).hexdigest()[:12]

def classifica(n):
    n["id"] = ident(n["titolo"])
    testo = n["titolo"] + " " + n["desc"]
    n["provincia"] = trova(testo, PROVINCE, n.pop("_hint", None) or "Sicilia")
    n["argomento"] = trova(testo, ARGOMENTI, "Altre notizie")
    n["fonte"] = nome_testata(n["fonte"])
    n["peso"] = priorita(n["fonte"])
    return n

def deduplica(notizie):
    notizie.sort(key=lambda n: -n["peso"])
    tenute = []
    for n in notizie:
        p = parole(n["titolo"])
        dup = None
        for t in tenute:
            q = t["_p"]
            if p and q and len(p & q) / len(p | q) >= 0.5: dup = t; break
        if dup:
            if not dup.get("img") and n.get("img"): dup["img"] = n["img"]
            altre = dup.setdefault("anche", [])
            if n["fonte"] != dup["fonte"] and all(a["fonte"] != n["fonte"] for a in altre) and len(altre) < 5:
                altre.append({"fonte": n["fonte"], "link": n["link"]})
        else:
            n["_p"] = p; tenute.append(n)
    for t in tenute: t.pop("_p", None); t.pop("_hint", None)
    return tenute

UA = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def apri(url, limite=250000, timeout=15):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read(limite).decode("utf8","ignore")

def risolvi_google(link):
    """Da un link news.google.com risale all'indirizzo reale dell'articolo."""
    try:
        art = link.split("/articles/")[1].split("?")[0]
        h = apri(link, 3000000, 20)
        sig = re.search(r'data-n-a-sg="([^"]+)"', h).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', h).group(1)
        req = ["Fbv4je", json.dumps(["garturlreq",[["X","X",["X"],None,None,1,1,"US:en",None,1,None,None,None,None,None,0,1],
               "X","X",1,[1,1,1],1,1,None,0,0,None,0], art, int(ts), sig]), None, "0"]
        body = urllib.parse.urlencode({"f.req": json.dumps([[req]])}).encode()
        r = urllib.request.urlopen(urllib.request.Request(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute", data=body,
            headers={**UA, "Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"}), timeout=25).read().decode("utf8","ignore")
        m = re.search(r'"(https?://(?!news\.google|www\.google)[^"\\]{15,})\\?"', r)
        return m.group(1) if m else None
    except Exception:
        return None

def og(url):
    """Immagine di copertina (og:image) dalla pagina dell'articolo."""
    try:
        h = apri(url, 300000)
        for pat in (r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]*content=["\']([^"\']+)',
                    r'<meta[^>]+name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image'):
            m = re.search(pat, h, re.I)
            if m:
                u = html.unescape(m.group(1)).strip()
                if u.startswith("//"): u = "https:" + u
                if u.startswith("http") and not re.search(r"logo|placeholder|default", u, re.I): return u
    except Exception:
        pass
    return None

# Google limita le richieste (errore 429): al massimo TETTO risoluzioni per esecuzione,
# con una piccola pausa. Il bot gira ogni 2 ore, quindi l'archivio si completa da solo.
TETTO = int(os.environ.get("TETTO_RISOLUZIONI", 220))
_lock = threading.Lock()
_contatore = [0]
def _permesso():
    with _lock:
        if _contatore[0] >= TETTO: return False
        _contatore[0] += 1
        return True

def arricchisci(n):
    """Risolve il link Google e recupera l'immagine mancante. Ogni notizia una sola volta."""
    if n.get("fatto"): return n
    if "news.google.com" in n["link"]:
        if not _permesso(): return n          # tetto raggiunto: al prossimo giro
        time.sleep(0.6)
        vero = risolvi_google(n["link"])
        if vero: n["link"] = vero
        else: return n          # riproveremo al prossimo giro
    if not n.get("img"): n["img"] = og(n["link"])
    n["fatto"] = 1
    return n

def main():
    with ThreadPoolExecutor(16) as ex:
        nuove = [n for lst in ex.map(scarica, FEED.items()) for n in lst]
    limite = (datetime.now(ROMA) - timedelta(days=2)).date()
    per_giorno = {}
    for n in nuove:
        g = n["data"][:10]
        if g >= limite.isoformat(): per_giorno.setdefault(g, []).append(classifica(n))
    os.makedirs(DIR, exist_ok=True)
    conteggi = {}
    for g, lst in per_giorno.items():
        f = os.path.join(DIR, g + ".json")
        vecchie = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else []
        tutte = deduplica(vecchie + lst)
        tutte.sort(key=lambda n: n["data"], reverse=True)
        with ThreadPoolExecutor(5) as ex: tutte = list(ex.map(arricchisci, tutte))
        print(f"  link risolti in questa esecuzione: {_contatore[0]}/{TETTO}")
        tutte.sort(key=lambda n: n["data"], reverse=True)
        json.dump(tutte, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",",":"))
        conteggi[g] = len(tutte)
        print(f"{g}: {len(tutte)} notizie")
    giorni = sorted((x[:-5] for x in os.listdir(DIR) if re.match(r"\d{4}-\d\d-\d\d\.json$", x)), reverse=True)
    json.dump(giorni, open(os.path.join(DIR, "index.json"), "w"))
    json.dump({"aggiornato": datetime.now(ROMA).isoformat(timespec="minutes"),
               "notizie_oggi": conteggi.get(datetime.now(ROMA).date().isoformat(), 0)},
              open(os.path.join(DIR, "stato.json"), "w"))

if __name__ == "__main__":
    main()
