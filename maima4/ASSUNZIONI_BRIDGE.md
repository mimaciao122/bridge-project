# Assunzioni esplicite per l'integrazione dell'agente locale con il bridge

Questo documento descrive le assunzioni che motivano il design del bridge e il
contract HTTP esposto. È pensato per essere verificato rapidamente da chi
conosce l'agente reale.

## 1. Come parla l'agente al bridge

- L'agente locale chiama un endpoint HTTP locale sul bridge:
  `POST /v1/bridge/request`.
- La comunicazione è sincrona: l'agente invia una richiesta e attende la
  risposta prima di proseguire.
- Il bridge è esplicitamente progettato come un gateway locale, non come un
  servizio remoto su internet.

## 2. Cosa passa l'agente

Il payload JSON inviato al bridge include:

- `operation`: il tipo di operazione richiesta, come `summarize`.
- `payload`: il testo grezzo da processare.
- `sensitivity`: un indicatore di sensibilità del contenuto, ad esempio
  `internal`.
- `max_output_tokens`: un limite sul numero massimo di token/righe di output.

Il bridge non permette all'agente di inviare `source_id` direttamente nella
body della richiesta: la sorgente viene assegnata in modo affidabile dal bridge
in base all'API key fornita.

## 3. Come si autentica l'agente

- L'autenticazione avviene tramite header HTTP `X-Bridge-Key`.
- Il bridge ha una mappatura configurabile (`BRIDGE_AGENTS_JSON`) tra la chiave
  e il `source_id` autorizzato.
- Questo significa che la fiducia si basa su una chiave locale per ogni agente,
  non su un token esterno o su un login dell'utente.

## 4. Cosa si assume qui rispetto all'agente reale

- L'agente reale deve poter emettere una richiesta HTTP locale con header.
- L'agente reale deve sapere solo il `operation`, il `payload`, il livello di
  sensibilità e il limite di output.
- L'agente reale non deve conoscere né generare `request_id` né `source_id`.
- L'agente reale non deve parlare direttamente con i provider esterni;
  questo è compito del bridge.

## 5. Cosa può essere diverso nel sistema reale

- L'agente reale potrebbe non parlare HTTP: in quel caso dovremo aggiungere un
  binding locale diverso (es. chiamata di libreria o IPC).
- L'agente reale potrebbe avere un formato di payload più ricco. In tal caso,
  la traduzione verso lo schema `BridgeRequest` deve essere fatta all'interno
  dell'adattatore tra agente e bridge.
- L'agente reale potrebbe già gestire l'autenticazione in modo diverso. Se
  succede, possiamo mantenere l'API key come fall-back e introdurre un wrapper
  d'autenticazione specifico.

## 6. Punti di verifica rapida

- L'agente può inviare `POST /v1/bridge/request` con `Content-Type: application/json`.
- L'agente invia `X-Bridge-Key` e riceve `401` se è mancante o non valido.
- Il bridge risponde sempre con lo stesso shape di `BridgeResponse`.
- Il bridge usa la chiave per ricavare la `source_id` e non accetta `source_id` nella body.
