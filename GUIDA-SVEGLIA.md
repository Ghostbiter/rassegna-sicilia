# La sveglia esterna (cron-job.org)

GitHub esegue le raccolte programmate "quando può": in pratica la prima della
giornata arriva verso le 11, quindi di prima mattina la rassegna resta ferma.
Questa sveglia esterna chiama GitHub ogni ora, sempre, anche a computer spento.

Serve una volta sola, poi si dimentica.

---

## 1. Crea la chiave di accesso su GitHub

1. Vai su https://github.com/settings/personal-access-tokens/new
2. **Token name**: `sveglia rassegna`
3. **Expiration**: 1 anno (o "No expiration")
4. **Repository access** → *Only select repositories* → scegli **rassegna-sicilia**
5. **Permissions** → *Repository permissions* → cerca **Actions** → metti **Read and write**
6. In fondo, **Generate token**
7. **Copia la chiave** (inizia con `github_pat_...`). Si vede una volta sola:
   se la perdi, ne generi un'altra e cancelli questa.

Questa chiave permette **solo** di avviare le raccolte su questo progetto.
Non dà accesso ad altro, e si può revocare quando vuoi dalla stessa pagina.

## 2. Crea la sveglia su cron-job.org

1. Registrati su https://cron-job.org (gratuito)
2. **Create cronjob**
3. **Title**: `Rassegna Sicilia`
4. **URL**:

       https://api.github.com/repos/Ghostbiter/rassegna-sicilia/actions/workflows/aggiorna.yml/dispatches

5. **Schedule**: *Every hour* — minuto **5** (o quello che preferisci)
6. Apri **Advanced**:
   - **Request method**: `POST`
   - **Request body**:

         {"ref":"main"}

   - **Headers** (tre righe):

         Authorization: Bearer LA_TUA_CHIAVE
         Accept: application/vnd.github+json
         Content-Type: application/json

7. **Create**

## 3. Verifica

Su cron-job.org premi **Test run**: deve rispondere **204 No Content**
(è la risposta giusta: GitHub ha accettato e non risponde altro).

Poi, dopo un minuto, guarda
https://github.com/Ghostbiter/rassegna-sicilia/actions:
deve comparire una raccolta nuova.

Sul sito, in **? Guida**, l'elenco "Ultime raccolte" mostrerà le raccolte
notturne e mattutine anche a Mac spento.

---

## Se qualcosa non va

| Risposta | Significato | Cosa fare |
|---|---|---|
| `204` | tutto a posto | niente |
| `401` | chiave sbagliata o scaduta | rigenera la chiave (passo 1) |
| `403` | alla chiave manca il permesso | rimetti **Actions: Read and write** |
| `404` | indirizzo o nome file errato | ricontrolla l'URL del passo 4 |

La chiave resta salvata su cron-job.org. Se un giorno vuoi chiudere tutto,
cancella la sveglia lì e revoca la chiave su GitHub.
