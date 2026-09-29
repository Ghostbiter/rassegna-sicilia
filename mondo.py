#!/usr/bin/env python3
"""Scenario internazionale, una edizione al giorno, per l'analisi di fase.

Raccoglie le notizie dal mondo della stampa italiana ed estera e per ogni giornata misura:
- quanto spazio prende ogni area geopolitica e ogni tema (anche stampa italiana contro estera);
- quali storie sono riprese da più testate, e come le titola ciascuna;
- quali parole salgono, restano al centro o escono dall'agenda rispetto ai giorni prima.
Salva docs/data/mondo/AAAA-MM-GG.json, index.json (le edizioni) e serie.json (le tendenze).
Solo libreria standard.

Gira dentro la raccolta oraria ma lavora una volta sola al giorno: alla prima raccolta dalle
ORA in poi, se l'edizione di oggi non c'è ancora. `python3 mondo.py --forza` la rifà subito."""
import re, os, sys, json, html, math, urllib.request, xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data", "mondo")
ORA = 6          # l'edizione si prepara alla prima raccolta dopo le 6 del mattino
FINESTRA = 24    # ore coperte da un'edizione
MINIMO = 60      # meno articoli di così vuol dire feed irraggiungibili: si riprova al giro dopo
STORICO = 60     # edizioni tenute nelle tendenze

# (testata, indirizzo, lingua, stampa). L'ordine conta: quando più testate danno la stessa
# storia, il titolo mostrato è quello della testata che viene prima.
GN = "https://news.google.com/rss/headlines/section/topic/WORLD?"
FEED = [
 ("ANSA", "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml", "it", "it"),
 ("Rai News", "https://www.rainews.it/rss/esteri", "it", "it"),
 ("Corriere della Sera", "https://xml2.corriereobjects.it/rss/esteri.xml", "it", "it"),
 ("la Repubblica", "https://www.repubblica.it/rss/esteri/rss2.0.xml", "it", "it"),
 ("Il Sole 24 Ore", "https://www.ilsole24ore.com/rss/mondo.xml", "it", "it"),
 ("AGI", "https://www.agi.it/estero/rss", "it", "it"),
 ("Il Post", "https://www.ilpost.it/mondo/feed/", "it", "it"),
 ("Il Fatto Quotidiano", "https://www.ilfattoquotidiano.it/mondo/feed/", "it", "it"),
 ("Internazionale", "https://www.internazionale.it/sitemaps/rss.xml", "it", "it"),
 ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "en", "estero"),
 ("The Guardian", "https://www.theguardian.com/world/rss", "en", "estero"),
 ("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "en", "estero"),
 ("Le Monde", "https://www.lemonde.fr/international/rss_full.xml", "fr", "estero"),
 ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada", "es", "estero"),
 ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en", "estero"),
 ("France 24", "https://www.france24.com/en/rss", "en", "estero"),
 ("Politico Europe", "https://www.politico.eu/feed/", "en", "estero"),
 ("NPR", "https://feeds.npr.org/1004/rss.xml", "en", "estero"),
 ("DW", "https://rss.dw.com/xml/rss-en-world", "en", "estero"),
 ("South China Morning Post", "https://www.scmp.com/rss/91/feed", "en", "estero"),
 # Google News "Mondo": aggiunge le altre testate (la fonte vera è nel titolo)
 ("GN it", GN + "hl=it&gl=IT&ceid=IT:it", "it", "it"),
 ("GN en", GN + "hl=en-US&gl=US&ceid=US:en", "en", "estero"),
]

# Parole chiave. Minuscole = senza distinzione di maiuscole, parola intera; "*" in fondo =
# qualunque finale (negoziat* prende negoziato, negoziati...); con una maiuscola = esattamente
# così (US, UE, NATO: evita "us" inglese o "ai" italiano).
AREE = {
 "Russia e Ucraina": ["russia","russo","russa","russi","russe","russian","russians","russie","rusia","ruso","rusa",
   "mosca","moscow","moscou","moscú","cremlino","kremlin","putin","lavrov","peskov","medvedev","ucraina","ucraino",
   "ucraini","ucraine","ukrain*","ucrania*","kiev","kyiv","zelensky*","zelenski*","donbass","donbas","donetsk",
   "luhansk","crimea","crimée","kharkiv","kherson","zaporizhzhia","odessa","bielorussia","belarus","biélorussie",
   "lukashenko","moldova","moldavia"],
 "Medio Oriente": ["medio oriente","middle east","moyen-orient","oriente medio","israel*","israël*","gaza","hamas",
   "hezbollah","libano","lebanon","liban","líbano","beirut","beyrouth","cisgiordania","west bank","cisjordanie",
   "palestin*","netanyahu","iran*","teheran","tehran","téhéran","khamenei","siria","syria*","syrie","damasco",
   "damascus","iraq","irak","baghdad","yemen","houthi*","arabia saudita","saudi*","riad","riyadh","qatar","doha",
   "emirati","emirates","egitto","egypt*","égypte","egipto","cairo","giordania","turchia","turkey","türkiye",
   "turquie","turquía","erdogan","erdoğan","ankara","curdi","kurd*"],
 "Stati Uniti": ["stati uniti","united states","états-unis","estados unidos","USA","US","U.S.","americano",
   "americani","americana","americane","washington","casa bianca","white house","maison blanche","casa blanca",
   "trump","vance","rubio","hegseth","bessent","congresso","congress","pentagono","pentagon","democratici",
   "repubblicani","republican*","democrat*","biden","obama","new york","california","texas","Fed","canada",
   "canadese","canadian","carney","ottawa"],
 "Europa e UE": ["unione europea","european union","union européenne","unión europea","UE","EU","Ue","bruxelles",
   "brussels","bruselas","commissione europea","european commission","parlamento europeo","european parliament",
   "von der leyen","kallas","eurozona","eurozone","BCE","ECB","lagarde","germania","germany","allemagne","alemania",
   "tedesco","tedeschi","tedesca","german","berlino","berlin","merz","AfD","francia","france","francese","francesi",
   "french","parigi","paris","macron","spagna","spain","espagne","españa","spagnolo","spanish","sánchez","madrid",
   "regno unito","united kingdom","UK","britain","british","britannico","britannici","gran bretagna","royaume-uni",
   "reino unido","londra","london","londres","starmer","farage","polonia","poland","pologne","polish","varsavia",
   "warsaw","tusk","ungheria","hungary","hongrie","orban","orbán","olanda","paesi bassi","netherlands","dutch",
   "belgio","belgium","austria","grecia","greece","portogallo","portugal","romania","bulgaria","serbia","kosovo",
   "bosnia","balcani","balkans","croazia","slovacchia","slovakia","repubblica ceca","czech","svezia","sweden",
   "norvegia","norway","finlandia","finland","danimarca","denmark","groenlandia","greenland","svizzera",
   "switzerland","irlanda","ireland","baltic*","lituania","lettonia","estonia"],
 "Italia nel mondo": ["meloni","tajani","crosetto","farnesina","palazzo chigi","mattarella","italia","italy","italie",
   "italiano","italiani","italiana","italiane","italian"],
 "Cina e Asia": ["cina","china","chine","cinese","cinesi","chinese","chinois*","chino","pechino","beijing","pékin",
   "pekín","Xi","xi jinping","taiwan","taipei","hong kong","giappone","japan","japon","japón","giapponese","japanese",
   "tokyo","tokio","corea","korea*","corée","seul","seoul","pyongyang","kim jong*","india","indian","indiano","inde",
   "modi","new delhi","nuova delhi","pakistan*","afghanistan","afghan*","taliban*","talebani","indonesia",
   "filippine","philippines","vietnam","thailandia","thailand","cambogia","cambodia","myanmar","birmania",
   "australia","australian","bangladesh","nepal","sri lanka","asia","asian","asiatico","indo-pacific*",
   "indopacifico","ASEAN","mar cinese meridionale","south china sea"],
 "Africa": ["africa","african*","africano","africani","afrique","áfrica","sahel","mali","niger","burkina*","sudan",
   "khartoum","darfur","etiopia","ethiopia","éthiopie","somalia","kenya","nigeria","congo","RDC","DRC","libia",
   "libya","libye","tripoli","bengasi","benghazi","haftar","tunisia","tunisie","túnez","algeria","algérie","marocco",
   "morocco","maroc","marruecos","senegal","sudafrica","south africa","afrique du sud","ciad","tchad","eritrea",
   "ruanda","rwanda","mozambico","mozambique","uganda","camerun","cameroon","cameroun","zimbabwe","tanzania","ghana",
   "costa d'avorio","ivory coast","côte d'ivoire","madagascar","angola","sud sudan","south sudan"],
 "America Latina": ["america latina","latin america","amérique latine","américa latina","sudamerica",
   "south america","brasile","brazil","brésil","brasil","lula","bolsonaro","argentina","argentine","milei",
   "buenos aires","venezuela","maduro","caracas","messico","mexico","mexique","méxico","sheinbaum","colombia",
   "colombie","petro","cile","chile","chili","perù","peru","pérou","perú","bolivia","ecuador","équateur","cuba",
   "l'avana","havana","la habana","nicaragua","haiti","haïti","uruguay","paraguay","panama","panamá","guatemala",
   "honduras","el salvador","bukele","caraibi","caribbean"],
 "Organismi internazionali": ["ONU","UN","Onu","nazioni unite","united nations","nations unies","naciones unidas",
   "guterres","NATO","Nato","OTAN","Otan","alleanza atlantica","rutte","G7","G20","BRICS","Brics","FMI","Fmi","IMF",
   "WTO","OMS","Oms","WHO","banca mondiale","world bank","corte penale internazionale",
   "international criminal court","ICC","CPI","Cpi","corte internazionale di giustizia",
   "international court of justice","ICJ","consiglio di sicurezza","security council","unesco","unicef","unhcr",
   "cop30","cop 30"],
}
TEMI = {
 "Guerra e sicurezza": ["guerra","guerre","war","wars","attacc*","attack*","attaque*","ataque*","raid","raids",
   "bombard*","bomb*","missil*","drone","droni","drones","esercito","army","armée","ejército","militar*",
   "militair*","soldat*","soldier*","truppe","troops","troupes","tropas","offensiv*","armi","weapons","armes",
   "armas","nuclear*","nucleare","nucléaire","terroris*","ostagg*","hostage*","otage*","rehén*","uccis*","killed",
   "tués","muertos","morti","strike","strikes","frappe*","invasion*","invasione","cecchin*","esplosion*",
   "explosion*","difesa","defence","defense","défense","defensa","riarmo","rearm*","sicurezza","security"],
 "Diplomazia e negoziati": ["negoziat*","negotiat*","négociat*","negociac*","colloqui","talks","pourparlers",
   "accordo","accordi","agreement","deal","accord","acuerdo","tregua","truce","trêve","ceasefire",
   "cessate il fuoco","cessez-le-feu","alto el fuego","vertice","summit","sommet","cumbre","incontr*","meeting",
   "meets","rencontre","diplomazi*","diplomat*","ambasciat*","ambassad*","embassy","embajad*","sanzion*",
   "sanction*","sanciones","mediazion*","mediat*","médiat*","pace","peace","paix","paz","trattat*","treaty",
   "traité","tratado","telefonata","phone call","visita","visite"],
 "Politica ed elezioni": ["elezion*","election*","élection*","eleccion*","elettoral*","electoral","voto","vote",
   "votes","voting","scrutin","sondagg*","poll","polls","sondage*","encuesta*","governo","government",
   "gouvernement","gobierno","parlament*","parliament*","premier","prime minister","primo ministro",
   "premier ministre","primer ministro","presidenziali","presidential","présidentielle","partit*","party","parti",
   "partido","coalizion*","coalition","coalición","opposizion*","opposition","oposición","dimission*","resign*",
   "démission*","dimisión","referendum","référendum","referéndum","candidat*","campagna elettorale","campaign",
   "campagne","campaña","destra","right-wing","far-right","estrema destra","extrême droite","ultraderecha",
   "sinistra","left-wing","gauche","izquierda","populis*","golpe","coup","colpo di stato"],
 "Economia e commercio": ["dazi","dazio","tariff*","droits de douane","aranceles","commerci*","trade","commerce",
   "comercio","econom*","mercat*","market*","marché*","borsa","borse","stock*","bourse","inflazione","inflation",
   "inflación","petrolio","oil","pétrole","petróleo","gas","energia","energy","énergie","energía","pil","Pil",
   "GDP","PIB","banca","banche","bank*","tassi","rates","taux","debito","debt","dette","deuda","crescita","growth",
   "croissance","crecimiento","recession*","récession","recesión","export*","import*","investiment*",
   "investment*","industri*","chip","chips","semicondutt*","semiconductor*","aziend*","compan*","impres*","lavoro",
   "jobs","emploi","empleo","sciopero","scioperi","grève","huelga","bilancio","budget","presupuesto","tasse",
   "taxes","impôts","impuestos","dollaro","dollar","euro","yuan","bitcoin","cripto*","crypto*"],
 "Diritti e crisi umanitarie": ["migrant*","migranti","migrazion*","migration*","migración","immigra*","inmigra*",
   "rifugiat*","refugee*","réfugié*","refugiad*","profugh*","asilo","asylum","asile","sbarc*","naufrag*",
   "shipwreck","deport*","espulsion*","expulsion*","rimpatr*","diritti","human rights","droits de l'homme",
   "derechos humanos","protest*","manifestant*","manifestazion*","repression*","repressione","répression",
   "represión","arrest*","detenut*","prisoner*","prisonnier*","tortur*","censura","censorship","giornalist*",
   "journalist*","donne","women","femmes","mujeres","lgbt*","razzis*","racis*","genocid*","génocide","carestia",
   "famine","hambruna","fame","hunger","umanitari*","humanitarian","humanitaire","humanitari*","aiuti","aid"],
 "Clima e disastri": ["clima","climat*","climate","cambio climático","emission*","émission*","emisiones",
   "alluvion*","flood*","inondation*","inundacion*","siccità","drought","sécheresse","sequía","incendi","incendio",
   "wildfire*","incendie*","uragan*","hurricane*","ouragan*","huracán","tifon*","typhoon*","ciclon*","cyclone*",
   "terremot*","earthquake*","séisme*","sisma","rinnovabil*","renewable*","renouvelable*","carbone","coal",
   "charbon","ambient*","environment*","environnement","medio ambiente","heatwave","canicule","ola de calor",
   "ghiacciai","glacier*","cop30"],
 "Tecnologia": ["intelligenza artificiale","artificial intelligence","intelligence artificielle",
   "inteligencia artificial","AI","IA","chatgpt","openai","anthropic","musk","tesla","spacex","starlink","big tech",
   "google","apple","microsoft","nvidia","tiktok","social network","social media","réseaux sociaux",
   "redes sociales","cyber*","hacker*","hacking","algoritm*","algorithm*","satellit*"],
}

def regole(diz):
    """Per ogni voce due espressioni: una sul testo in minuscolo, una esatta (per le sigle)."""
    out = {}
    for k, parole in diz.items():
        ins, esa = [], []
        for w in parole:
            pre = w.endswith("*"); w = w.rstrip("*")
            p = (r"\b" if w[0].isalnum() else "") + re.escape(w) + ("" if pre or not w[-1].isalnum() else r"\b")
            (esa if any(c.isupper() for c in w) else ins).append(p)
        out[k] = tuple(re.compile("|".join(l)) if l else None for l in (ins, esa))
    return out
R_AREE, R_TEMI = regole(AREE), regole(TEMI)

def punteggi(testo, reg):
    basso = testo.lower()
    return {k: (len(i.findall(basso)) if i else 0) + (len(e.findall(testo)) if e else 0) for k, (i, e) in reg.items()}

# --- parole della giornata -------------------------------------------------------------
VUOTE = set("""il lo la i gli le un uno una di a da in con su per tra fra del dello della dei degli delle al allo alla
ai agli alle dal dallo dalla dai dagli dalle nel nello nella nei negli nelle sul sullo sulla sui sugli sulle col coi
e ed o od ma se che chi cui non più piu anche come dove quando perché perche mentre dopo prima poi già gia ancora
sempre mai molto tanto tutto tutti tutta tutte ogni altro altri altra altre questo questa questi queste quello quella
quelli quelle suo sua suoi sue loro nostro nostra mio mia essere è sono era erano stato stata stati state sarà sara
saranno ha hanno aveva avevano avere fa fare fanno può puo possono deve devono vuole vogliono ci si ne lui lei noi voi
io tu li oggi ieri domani ora ore anni anno giorni giorno mesi mese settimana dice dicono detto secondo contro senza
verso sotto sopra oltre circa quasi solo ecco cosa così cosi via tre quattro cinque sei sette otto nove dieci cento
mille mila milioni miliardi nuovo nuova nuovi nuove grande grandi primo ultimo ultima ultime ultimi video foto live
diretta news notizie aggiornamenti tra dell nell sull dall all quale quali parla parlano arriva arrivano
the an and or but if of to in on at by for with from into onto over under about after before between during without
within as is are was were be been being has have had having do does did will would shall should can could may might
must not no nor so than that this these those there here what which who whom whose when where why how all any both
each few more most other some such own same too very just also only its it his her their our your my we you they he
she them him me says said say new latest update updates watch analysis opinion year years day days week weeks month
months time times first last one two three four five six seven eight nine ten hundreds thousands million millions
billion billions report reports amid up out off again still now today yesterday tomorrow could get gets got back
le la les un une des de du et ou mais si que qui quoi dont où à au aux en dans sur sous par pour avec sans contre
entre vers chez ce cet cette ces son sa ses leur leurs mon ma mes notre nos votre vos il elle ils elles on nous vous
je se ne pas plus moins très tout tous toute toutes est sont était été être ont avait avoir fait faire peut doit
comme après avant depuis pendant encore aussi déjà selon lors alors deux trois quatre cinq ans jour jours semaine
mois heure heures nouveau nouvelle nouveaux direct vidéo
el los las lo unos unas del al y e o u pero quien quién cual cuál cuando cuándo donde dónde cómo por para sin sobre
hacia desde hasta tras ante bajo sus mi mis tu tus nuestro se ni más menos muy toda todas es son fue fueron ser
sido está están estaba han había haber hace hacer puede pueden debe después antes durante también ya aún todavía
según años año día días mes meses hora horas nueva dos cuatro
annuncia annunciano chiede chiedono afferma dichiara apre aprono lancia torna tornano scatta spiega avverte parla
sarebbe potrebbe fatto caso casi tempo parte volta punto pronto pronti pronta""".split())
# nomi composti e sinonimi fra lingue: contano come una parola sola
FRASI = [(re.compile(a, re.I), b) for a, b in [
 (r"\bstati uniti\b|\bunited states\b|\bétats-unis\b|\bestados unidos\b|\bU\.S\.(?!\w)", "Usa"),
 (r"\bcasa bianca\b|\bwhite house\b|\bmaison blanche\b|\bcasa blanca\b", "CasaBianca"),
 (r"\bunione europea\b|\beuropean union\b|\bunion européenne\b|\bunión europea\b", "Ue"),
 (r"\bnazioni unite\b|\bunited nations\b|\bnations unies\b|\bnaciones unidas\b", "Onu"),
 (r"\bcessate il fuoco\b|\bceasefire\b|\bcessez-le-feu\b|\balto el fuego\b", "CessateIlFuoco"),
 (r"\bmedio oriente\b|\bmiddle east\b|\bmoyen-orient\b|\boriente medio\b", "MedioOriente"),
 (r"\bstriscia di gaza\b|\bgaza strip\b|\bbande de gaza\b|\bfranja de gaza\b", "Gaza"),
 (r"\bregno unito\b|\bunited kingdom\b|\broyaume-uni\b|\breino unido\b", "RegnoUnito"),
 (r"\bcorea del nord\b|\bnorth korea\b|\bcorée du nord\b", "CoreaDelNord"),
 (r"\bcorea del sud\b|\bsouth korea\b|\bcorée du sud\b", "CoreaDelSud"),
 (r"\bintelligenza artificiale\b|\bartificial intelligence\b|\bintelligence artificielle\b", "IntelligenzaArtificiale"),
 (r"\bhong kong\b", "HongKong"), (r"\bxi jinping\b", "Xi"), (r"\bvon der leyen\b", "VonDerLeyen"),
]]
SIGLE = {"US": "usa", "USA": "usa", "UE": "ue", "EU": "ue", "UN": "onu", "ONU": "onu", "UK": "regnounito",
         "NATO": "nato", "OTAN": "nato", "AI": "intelligenzaartificiale", "IA": "intelligenzaartificiale", "Xi": "xi"}
SINONIMI = {"ukraine": "ucraina", "ucrania": "ucraina", "russie": "russia", "rusia": "russia", "israël": "israele",
            "israel": "israele", "china": "cina", "chine": "cina", "syria": "siria", "syrie": "siria",
            "lebanon": "libano", "liban": "libano", "germany": "germania", "allemagne": "germania",
            "alemania": "germania", "europe": "europa", "tariffs": "dazi", "tariff": "dazi", "aranceles": "dazi",
            "migrants": "migranti", "migrantes": "migranti", "elections": "elezioni", "election": "elezioni",
            "élections": "elezioni", "elecciones": "elezioni", "war": "guerra", "guerre": "guerra", "peace": "pace",
            "paix": "pace", "paz": "pace", "turkey": "turchia", "türkiye": "turchia", "turquie": "turchia",
            "egypt": "egitto", "égypte": "egitto", "venezuela": "venezuela", "japan": "giappone", "japon": "giappone",
            "india": "india", "inde": "india", "brazil": "brasile", "brésil": "brasile", "brasil": "brasile",
            "mexico": "messico", "mexique": "messico", "méxico": "messico", "poland": "polonia", "pologne": "polonia",
            "france": "francia", "spain": "spagna", "espagne": "spagna", "españa": "spagna", "moscow": "mosca",
            "moscou": "mosca", "kyiv": "kiev", "kremlin": "cremlino", "hostages": "ostaggi", "otages": "ostaggi",
            "sanctions": "sanzioni", "nuclear": "nucleare", "nucléaire": "nucleare", "palestinians": "palestinesi",
            "palestiniens": "palestinesi", "palestinos": "palestinesi", "greenland": "groenlandia",
            "tariffe": "dazi", "talks": "colloqui", "steel": "acciaio", "acier": "acciaio", "acero": "acciaio",
            "truce": "tregua", "trêve": "tregua", "sanciones": "sanzioni", "drones": "droni", "missiles": "missili",
            "refugees": "rifugiati", "famine": "carestia", "hambruna": "carestia", "protests": "proteste",
            "protestas": "proteste", "coup": "golpe", "summit": "vertice", "sommet": "vertice", "cumbre": "vertice",
            "oil": "petrolio", "pétrole": "petrolio", "petróleo": "petrolio", "markets": "mercati",
            "marchés": "mercati", "mercados": "mercati", "army": "esercito", "troops": "truppe", "soldiers": "soldati",
            "vote": "voto", "government": "governo", "gouvernement": "governo", "gobierno": "governo",
            "president": "presidente", "président": "presidente", "minister": "ministro", "ministre": "ministro",
            "parliament": "parlamento", "parlement": "parlamento", "attack": "attacco", "attacks": "attacco",
            "attaque": "attacco", "ataque": "attacco", "killed": "morti", "muertos": "morti", "tués": "morti",
            "dead": "morti", "migrant": "migranti", "refugee": "rifugiati", "hostage": "ostaggi"}
MOSTRA = {"usa": "Usa", "casabianca": "Casa Bianca", "ue": "Ue", "onu": "Onu", "cessateilfuoco": "cessate il fuoco",
          "mediooriente": "Medio Oriente", "regnounito": "Regno Unito", "coreadelnord": "Corea del Nord",
          "coreadelsud": "Corea del Sud", "intelligenzaartificiale": "intelligenza artificiale",
          "hongkong": "Hong Kong", "xi": "Xi Jinping", "vonderleyen": "von der Leyen", "nato": "Nato"}
TENUTE = set(SIGLE.values())
# parole valide in ogni lingua: nomi composti, sigle ed equivalenze
COMUNI = TENUTE | set(SINONIMI.values()) | {b.lower() for _, b in FRASI}
_forme = {}   # parola -> Counter delle forme originali (per mostrarla con le maiuscole giuste)

def parole(titolo):
    for r, b in FRASI: titolo = r.sub(b, titolo)
    out = set()
    for w in re.findall(r"[^\W\d_]+", titolo):
        k = SIGLE.get(w) or w.lower()
        if k not in TENUTE and (len(k) < 3 or k in VUOTE): continue
        k = SINONIMI.get(k, k)
        out.add(k); _forme.setdefault(k, Counter())[w] += 1
    return out

def mostra(k):
    """Maiuscola solo per i nomi propri: se la parola compare anche in minuscolo, è un nome comune."""
    if k in MOSTRA: return MOSTRA[k]
    forme = _forme.get(k)
    if not forme or any(f.islower() for f in forme): return k
    return k.capitalize() if k.capitalize() in forme else forme.most_common(1)[0][0]   # "Cina", non "China"

# --- raccolta -------------------------------------------------------------------------
UA = {"User-Agent": "Mozilla/5.0 (RassegnaSiciliaBot; scenario internazionale)"}
ATOM = "{http://www.w3.org/2005/Atom}"
pulisci = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()

def data_di(s):
    s = (s or "").strip()
    try: d = parsedate_to_datetime(s)
    except Exception:
        try: d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def scarica(voce):
    ordine, (nome, url, lingua, stampa) = voce
    try:
        req = urllib.request.Request(url, headers=UA)
        root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        print("ERR", nome, str(e)[:70]); return nome, []
    out = []
    for it in list(root.iter("item")) + list(root.iter(ATOM + "entry")):
        titolo = pulisci(it.findtext("title") or it.findtext(ATOM + "title"))
        link = (it.findtext("link") or "").strip()
        if not link:
            e = it.find(ATOM + "link"); link = e.get("href", "") if e is not None else ""
        data = data_di(it.findtext("pubDate") or it.findtext(ATOM + "updated") or it.findtext(ATOM + "published"))
        if not titolo or not link or not data: continue
        fonte, desc = nome, pulisci(it.findtext("description") or it.findtext(ATOM + "summary"))
        if nome.startswith("GN"):
            fonte = (it.findtext("source") or "").strip()
            if " - " in titolo: titolo, f2 = titolo.rsplit(" - ", 1); fonte = fonte or f2
            desc = ""
        out.append({"titolo": titolo, "link": link, "fonte": fonte, "lingua": lingua, "stampa": stampa,
                    "data": data.astimezone(ROMA).isoformat(timespec="minutes"), "desc": desc[:300],
                    "_o": ordine, "_d": data})
    print("ok ", nome, len(out)); return nome, out

def chiave_testata(f):
    f = re.sub(r"^the\s+|\s+(news|online|\.it|\.com)$", "", f.lower().strip())
    return re.sub(r"\W+", "", f)

def primo(p, predefinito):
    if not p: return predefinito
    k = max(p, key=p.get)
    return k if p[k] else predefinito

def raggruppa(articoli):
    """Stessa storia = almeno due parole importanti in comune e un terzo delle parole del titolo.
    Ogni articolo si confronta solo con il titolo che apre il gruppo (niente catene)."""
    articoli.sort(key=lambda a: a["_d"], reverse=True)
    articoli.sort(key=lambda a: a["_o"])     # apre il gruppo la testata che viene prima, col pezzo più recente
    gruppi, indice = [], {}
    for a in articoli:
        p = a["_p"]
        comuni = Counter(i for w in p for i in indice.get(w, ()))
        g = min((i for i, c in comuni.items()
                 if c >= 2 and c / (len(p) + len(gruppi[i][0]["_p"]) - c) >= 1 / 3), default=None)
        if g is None:
            for w in p: indice.setdefault(w, []).append(len(gruppi))
            gruppi.append([a])
        else:
            gruppi[g].append(a)
    return gruppi

def quote(pesi, totale):
    return {k: round(100 * v / totale, 1) if totale else 0 for k, v in pesi.items()}

def main():
    forza = "--forza" in sys.argv
    adesso = datetime.now(ROMA)
    oggi = adesso.date().isoformat()
    f_oggi = os.path.join(DIR, oggi + ".json")
    if not forza and (os.path.exists(f_oggi) or adesso.hour < ORA):
        print("mondo: niente da fare (edizione di oggi già pronta, o prima delle %d)" % ORA); return
    with ThreadPoolExecutor(12) as ex:
        risultati = list(ex.map(scarica, enumerate(FEED)))
    inizio = adesso - timedelta(hours=FINESTRA)
    visti, articoli = set(), []
    for _, lst in risultati:
        for a in lst:
            k = (chiave_testata(a["fonte"]), re.sub(r"\W+", "", a["titolo"].lower()))
            if inizio <= a["_d"] <= adesso and k not in visti:
                visti.add(k); articoli.append(a)
    print(f"mondo: {len(articoli)} articoli nelle ultime {FINESTRA} ore")
    if len(articoli) < MINIMO:
        print("mondo: troppo pochi, riprovo alla prossima raccolta"); return

    # aree e temi: ogni articolo pesa 1, diviso fra le aree che nomina (in proporzione)
    pesi = {s: Counter() for s in ("tutti", "it", "estero")}
    pesi_t, classificati, classificati_s, classificati_t = Counter(), 0, Counter(), 0
    df = Counter()
    for a in articoli:
        testo = a["titolo"] + " . " + a["desc"]
        pa, pt = punteggi(testo, R_AREE), punteggi(testo, R_TEMI)
        a["area"], a["tema"] = primo(pa, ""), primo(pt, "")
        tot = sum(pa.values())
        if tot:
            classificati += 1; classificati_s[a["stampa"]] += 1
            for k, v in pa.items():
                if v: pesi["tutti"][k] += v / tot; pesi[a["stampa"]][k] += v / tot
        tt = sum(pt.values())
        if tt:
            classificati_t += 1
            for k, v in pt.items():
                if v: pesi_t[k] += v / tt
        a["_p"] = parole(a["titolo"])
    # Le parole si contano in italiano: dalla stampa estera valgono i nomi propri e le parole che
    # compaiono anche nei titoli italiani (Gaza, Trump, Hormuz...) più le equivalenze fra lingue.
    italiane = set().union(*(a["_p"] for a in articoli if a["lingua"] == "it"))
    for a in articoli:
        df.update(a["_p"] if a["lingua"] == "it" else {w for w in a["_p"] if w in italiane or w in COMUNI})
    q, q_it, q_es = (quote(pesi[s], n) for s, n in
                     (("tutti", classificati), ("it", classificati_s["it"]), ("estero", classificati_s["estero"])))
    qt = quote(pesi_t, classificati_t)

    # storie: gruppi di articoli, contate per numero di testate diverse
    storie = []
    for g in raggruppa(articoli):
        testa, testate = g[0], {}
        for a in g: testate.setdefault(chiave_testata(a["fonte"]), a)
        area = primo(Counter(a["area"] for a in g if a["area"]), testa["area"])
        tema = primo(Counter(a["tema"] for a in g if a["tema"]), testa["tema"])
        # una voce per testata (al massimo 12), tenendo sempre la prima italiana e la prima estera:
        # il sito mostra a ciascuna colonna il titolo della propria stampa
        lst = list(testate.values())
        prime = [next((a for a in lst if a["stampa"] == st), None) for st in ("it", "estero")]
        voci = sorted({id(a): a for a in lst[:12] + [a for a in prime if a]}.values(), key=lst.index)
        storie.append({"titolo": testa["titolo"], "link": testa["link"], "fonte": testa["fonte"],
                       "stampa": testa["stampa"], "area": area, "tema": tema,
                       "data": max(a["data"] for a in g), "n": len(testate),
                       "it": sum(1 for a in lst if a["stampa"] == "it"),
                       "testate": [{"fonte": a["fonte"], "titolo": a["titolo"], "link": a["link"], "stampa": a["stampa"]}
                                   for a in voci]})
    storie.sort(key=lambda s: (s["n"], s["data"]), reverse=True)   # più testate prima, poi la più recente
    tenute, scelte = [], set()
    def tieni(lst):
        for s in lst:
            if id(s) not in scelte: scelte.add(id(s)); tenute.append(s)
    tieni(storie[:80])
    for k in AREE: tieni([s for s in storie if s["area"] == k][:10])
    for k in TEMI: tieni([s for s in storie if s["tema"] == k][:6])
    tenute.sort(key=lambda s: -s["n"])

    # parole: confronto con le edizioni precedenti
    os.makedirs(DIR, exist_ok=True)
    edizioni = sorted((x[:-5] for x in os.listdir(DIR) if re.match(r"\d{4}-\d\d-\d\d\.json$", x) and x[:-5] < oggi),
                      reverse=True)
    prima = []
    for g in edizioni[:7]:
        try:
            e = json.load(open(os.path.join(DIR, g + ".json"), encoding="utf-8"))
            prima.append((e["articoli"], e["conteggi"], e["aree"]))
        except Exception:
            pass
    N = len(articoli)
    oggi_q = {k: v / N for k, v in df.items()}
    media = Counter()
    for n, c, _ in prima:
        for k, v in c.items(): media[k] += v / n / len(prima)
    ascesa, calo, stabili = [], [], []   # stabili: presenti quasi ogni giorno, né in ascesa né in calo
    if prima:
        for k, v in df.items():
            if v >= 4 and oggi_q[k] >= 2 * media[k]:
                ascesa.append((oggi_q[k] - media[k], k))
        for k, m in media.items():
            if m * N >= 4 and oggi_q.get(k, 0) <= m / 2:
                calo.append((m - oggi_q.get(k, 0), k))
        if len(prima) >= 2:
            giorni = [c for _, c, _ in prima] + [df]
            for k in set(df) | set(media):
                presenze = sum(1 for c in giorni if c.get(k, 0) >= 3)
                if presenze >= math.ceil(0.8 * len(giorni)) and media[k] / 2 < oggi_q.get(k, 0) < 2 * media[k]:
                    stabili.append(((media[k] * len(prima) + oggi_q.get(k, 0)) / len(giorni), k))
    fmt = lambda k: {"parola": mostra(k), "oggi": df.get(k, 0), "quota": round(100 * oggi_q.get(k, 0), 2),
                     "prima": round(100 * media.get(k, 0), 2)}
    # medie delle aree nei giorni precedenti, per il confronto sul sito
    media_aree = {k: round(sum(e.get(k, 0) for _, _, e in prima) / len(prima), 1) if prima else None for k in AREE}

    per_feed = Counter(a["_o"] for a in articoli)
    nome_feed = {"GN it": "Google News · Italia", "GN en": "Google News · internazionale"}
    edizione = {
        "giorno": oggi, "generato": adesso.isoformat(timespec="minutes"), "ore": FINESTRA,
        "articoli": N, "testate": len({chiave_testata(a["fonte"]) for a in articoli}),
        "stampa": {"it": sum(1 for a in articoli if a["stampa"] == "it"),
                   "estero": sum(1 for a in articoli if a["stampa"] == "estero")},
        "non_attribuiti": round(100 * (N - classificati) / N, 1),
        "aree": {k: q.get(k, 0) for k in AREE}, "aree_it": {k: q_it.get(k, 0) for k in AREE},
        "aree_estero": {k: q_es.get(k, 0) for k in AREE}, "aree_prima": media_aree,
        "edizioni_prima": len(prima),
        "temi": {k: qt.get(k, 0) for k in TEMI},
        "storie": tenute,
        "parole": {"oggi": [fmt(k) for k, _ in df.most_common(30)],
                   "ascesa": [fmt(k) for _, k in sorted(ascesa, reverse=True)[:15]],
                   "stabili": [fmt(k) for _, k in sorted(stabili, reverse=True)[:15]],
                   "calo": [fmt(k) for _, k in sorted(calo, reverse=True)[:15]]},
        "fonti": [[nome_feed.get(f[0], f[0]), f[3], per_feed[i]] for i, f in enumerate(FEED)],
        "conteggi": dict(df.most_common(400)),
    }
    with open(f_oggi, "w", encoding="utf-8") as fh:
        json.dump(edizione, fh, ensure_ascii=False, separators=(",", ":"))

    # indice delle edizioni e serie per le tendenze
    edizioni = sorted((x[:-5] for x in os.listdir(DIR) if re.match(r"\d{4}-\d\d-\d\d\.json$", x)), reverse=True)
    json.dump(edizioni, open(os.path.join(DIR, "index.json"), "w"))
    serie = {"giorni": [], "articoli": [], "aree": {k: [] for k in AREE}, "temi": {k: [] for k in TEMI}}
    for g in reversed(edizioni[:STORICO]):
        try: e = json.load(open(os.path.join(DIR, g + ".json"), encoding="utf-8"))
        except Exception: continue
        serie["giorni"].append(g); serie["articoli"].append(e["articoli"])
        for k in AREE: serie["aree"][k].append(e["aree"].get(k, 0))
        for k in TEMI: serie["temi"][k].append(e["temi"].get(k, 0))
    json.dump(serie, open(os.path.join(DIR, "serie.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"mondo: edizione del {oggi} pronta · {N} articoli, {edizione['testate']} testate, "
          f"{len(tenute)} storie · area principale: {max(q, key=q.get) if q else '-'}")

if __name__ == "__main__":
    main()
