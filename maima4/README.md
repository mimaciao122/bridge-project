# Bridge Project

Un ponte tra un assistente locale e un provider AI esterno (

## Cos'è

Immagina di avere un assistente che gira in locale e che, per certe operazioni,
ha bisogno di appoggiarsi a un modello AI più potente disponibile solo online.
Il problema è che non vuoi che l'assistente parli *direttamente* col mondo
esterno: nessun controllo su cosa esce, nessuna garanzia che i dati sensibili
restino dentro, nessuna traccia di cosa è successo.

Questo bridge sta in mezzo. L'assistente non chiama mai il provider esterno
da solo — passa sempre da qui, e ogni richiesta attraversa tre controlli in
sequenza prima di uscire:

1. **Whitelist** :l'operazione richiesta è autorizzata per quell'agente?
2. **Rate limit** :quell'agente ha superato i limiti di richieste/volume?
3. **Redazione** :email, IBAN, telefoni, importi e simili vengono oscurati
   automaticamente prima che il testo esca verso l'esterno.

Ogni decisione (accettata, accettata con redazione, o rifiutata) viene
scritta in un log di audit con hash di integrità, così è sempre verificabile
a posteriori se qualcosa è stato manomesso.

Se in futuro vuoi cambiare provider,
lo fai cambiando una variabile d'ambiente — l'interfaccia verso l'assistente
resta identica.

## Requisiti

- Python 3.9 o superiore
- `pip3` funzionante (su Mac, se `pip` da solo non viene riconosciuto, usa
  sempre `pip3` o `python3 -m pip`)

## Avvio rapido (senza provider esterni veri)

Questa modalità usa uno "stub" locale al posto di un vero provider AI, utile
per testare il bridge senza bisogno di chiavi API.

```bash
cd maima4
pip3 install -r requirements.txt
```

Poi, **tutti i comandi seguenti vanno lanciati nello stesso terminale**, uno
dopo l'altro, senza chiuderlo, le variabili d'ambiente impostate con `export`
valgono solo per la sessione di terminale in cui le scrivi:

```bash
export BRIDGE_AGENTS_JSON='{"chiave-super-segreta-1":"assistente-locale-1"}'
export USE_REAL_ADAPTER=0
export AUDIT_LOG_PATH=/tmp/audit_log.jsonl
python3 -m uvicorn bridge.http_server:app --host 127.0.0.1 --port 8000
```

Quando vedi in fondo `Uvicorn running on http://127.0.0.1:8000`, il server è
attivo. Apri quell'indirizzo nel browser: trovi una mini interfaccia web
("Ponte") per comporre e inviare richieste al bridge senza usare `curl`, con
un diagramma che mostra visivamente quali checkpoint la richiesta ha
attraversato. La documentazione tecnica interattiva generata da FastAPI è su
`http://127.0.0.1:8000/docs`.

Per fermare il server: torna al terminale e premi `Ctrl+C`.

### Perché il server potrebbe rifiutarsi di partire

Se vedi un errore tipo `BRIDGE_AGENTS_JSON non impostata`, è voluto: il bridge
non si avvia mai senza una lista esplicita di chiavi autorizzate, per non
rischiare di esporre un endpoint aperto per errore. Basta impostare la
variabile come mostrato sopra, nello stesso terminale da cui lanci `uvicorn`.

## Usare l'assistente locale di riferimento

C'è anche uno script pronto, `local_assistant.py`, che simula un assistente
reale: prende un testo e lo manda al bridge, mostrando la risposta.

Con il server già acceso (in un altro terminale, o in background), apri un
secondo terminale nella stessa cartella ed esegui:

```bash
python3 local_assistant.py "Contatta mario.rossi@example.com per il bonifico di 250 EUR"
```

oppure, in modalità interattiva (continua a chiederti testo finché non premi
Ctrl+C o dai riga vuota):

```bash
python3 local_assistant.py
```

## Usare un provider AI reale

### Hugging Face

```bash
export USE_REAL_ADAPTER=1
export BRIDGE_ADAPTER=huggingface
export HUGGINGFACE_API_TOKEN=la_tua_chiave
python3 bridge/main.py --operation summarize --payload "Testo da riassumere" --source-id assistente-1
```

Il token va creato gratuitamente su
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) la
Inference API oggi richiede sempre un token valido, le chiamate anonime non
sono più affidabili.

### Groq 
```bash
export USE_REAL_ADAPTER=1
export BRIDGE_ADAPTER=groq
export GROQ_API_KEY=la_tua_chiave
python3 bridge/main.py --operation summarize --payload "Testo da riassumere" --source-id assistente-1
```

Chiave gratuita su [console.groq.com/keys](https://console.groq.com/keys).

## Test

```bash
python3 test_step1_2_3.py
python3 test_step4_5.py
python3 -m pytest tests/ -q
```

## Variabili d'ambiente

Vedi `.env.example` per l'elenco completo. Le principali:

| Variabile | Default | Effetto |
|---|---|---|
| `BRIDGE_AGENTS_JSON` | — | **Obbligatoria per avviare il server.** Mappa `{"chiave": "source_id"}` per l'autenticazione HTTP |
| `EXTERNAL_AI_ENABLED` | `true` | Interruttore principale: se `false`, ogni operazione va in `deny`, anche se in whitelist |
| `USE_REAL_ADAPTER` | `false` | Se `true`, usa un provider reale invece dello stub |
| `BRIDGE_ADAPTER` | `huggingface` | Quale provider reale usare: `huggingface` o `groq` |
| `HUGGINGFACE_API_TOKEN` | — | Token Hugging Face (vedi sopra) |
| `HUGGINGFACE_MODEL` | `google/flan-t5-small` | Modello Hugging Face da usare |
| `GROQ_API_KEY` | — | API key Groq (vedi sopra) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modello Groq da usare |
| `AUDIT_LOG_PATH` | `audit_test.jsonl` | Percorso del file di audit log |

## Struttura del progetto

```
bridge/
├── core/
│   ├── contract.py       # schema BridgeRequest / BridgeResponse
│   ├── config.py
│   ├── factory.py
│   └── orchestrator.py   # ordine dei controlli: whitelist → rate limit → redazione
├── adapters/
│   ├── huggingface_adapter.py
│   ├── groq_adapter.py
│   └── external_ai_stub.py
├── policy/
│   └── engine.py          # whitelist, rate limit, redazione
├── audit/
│   └── logger.py           # log firmato con hash verificabile
└── static/
    └── index.html          # mini UI di test
local_agent_client.py        # client di esempio, chiama il bridge via HTTP
local_assistant.py           # assistente locale minimo, pronto all'uso
```

## Problemi comuni

**"command not found: pip"** su Mac usa `pip3` o `python3 -m pip` al posto
di `pip`.

**Il server si rifiuta di partire con un errore su `BRIDGE_AGENTS_JSON`**
la variabile va impostata con `export` nello *stesso* terminale, appena prima
di lanciare `uvicorn`. Se chiudi il terminale o ne apri uno nuovo, va
reimpostata.

**Ho modificato `bridge/static/index.html` ma il browser mostra ancora la
versione vecchia** è quasi sempre cache del browser, non un problema del
server. Prova un hard refresh (`Cmd+Shift+R` su Mac), oppure apri la pagina
in una finestra privata/anonima, oppure riavvia il server su una porta mai
usata prima (es. `--port 9091`) per essere sicuro al 100% che non ci sia
nulla in cache legato a quell'indirizzo.
