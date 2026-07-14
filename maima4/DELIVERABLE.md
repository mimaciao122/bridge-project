# Deliverable: Local-to-External AI Bridge

Questo repository consegna il ponte software tra:
- un assistente locale esistente
- un provider AI esterno controllato

Il bridge gestisce policy, audit e adapter esterni.
L’assistente locale chiama solo il bridge; non accede direttamente al provider esterno.

## Contenuto consegnato
- `bridge/` — componente bridge completo
- `bridge/main.py` — CLI di esempio
- `test_step1_2_3.py` — verifica locale/stub
- `test_step4_5.py` — verifica provider reale + feature flag
- `requirements.txt`
- `README.md`

## Uso rapido
1. Installare dipendenze:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Stub locale:
   ```bash
   export USE_REAL_ADAPTER=0
   python3 bridge/main.py --operation summarize --payload "Testo da riassumere" --source-id assistente-1
   ```

3. Provider reale:
   ```bash
   export USE_REAL_ADAPTER=1
   export HUGGINGFACE_API_TOKEN=tuo_token
   python3 bridge/main.py --operation summarize --payload "Testo da riassumere" --source-id assistente-1
   ```

4. Validazione tests:
   ```bash
   python3 test_step1_2_3.py
   python3 test_step4_5.py
   ```

## Integrazione
1. L’assistente locale costruisce `BridgeRequest`.
2. Chiama il bridge.
3. Riceve `BridgeResponse`.
4. Non chiama direttamente il provider esterno.

## File chiave
- `bridge/core/contract.py`
- `bridge/core/orchestrator.py`
- `bridge/core/config.py`
- `bridge/core/factory.py`
- `bridge/policy/engine.py`
- `bridge/adapters/external_ai_stub.py`
- `bridge/adapters/huggingface_adapter.py`
- `bridge/audit/logger.py`
- `bridge/main.py`
