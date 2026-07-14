"""
Audit log — Step 3.

Requisiti chiave (dal piano):
  - registra OGNI scambio (richiesta, risposta, chi, quando) — compresi i deny
  - è indipendente dal bridge stesso: anche se il bridge ha un bug,
    il log deve restare leggibile e verificabile
  - non alterabile a posteriori: se qualcuno modifica una riga passata,
    deve essere rilevabile

Come è ottenuto:
  - file JSONL append-only (una riga = un evento, mai riscritta)
  - hash chain: ogni riga contiene l'hash della riga precedente + il proprio
    hash. Cambiare o rimuovere una riga vecchia rompe la catena da lì in poi,
    e `verify_integrity()` lo rileva.
  - non salviamo mai il payload originale in chiaro: solo un digest
    (vedi `payload_digest` in AuditRecord, calcolato a monte in orchestrator.py)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bridge.core.contract import AuditRecord


GENESIS_HASH = "0" * 64  # hash "precedente" per la primissima riga del log


def _record_hash(prev_hash: str, record_json: str) -> str:
    return hashlib.sha256((prev_hash + record_json).encode("utf-8")).hexdigest()


def payload_digest(raw_payload: str) -> str:
    """Digest del payload ORIGINALE, da usare in AuditRecord.
    Mai il testo in chiaro nel log, solo questo hash: permette di correlare
    due richieste con lo stesso contenuto senza esporre il contenuto stesso."""
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


class AuditLogger:
    """Logger indipendente: nessuna dipendenza dal resto del bridge.
    Se policy engine o adapter esplodono, questo oggetto continua a
    funzionare da solo — riceve solo l'AuditRecord già costruito."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def _last_hash(self) -> str:
        last_line = None
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            return GENESIS_HASH
        return json.loads(last_line)["_hash"]

    def append(self, record: AuditRecord) -> str:
        """Scrive il record in append e ritorna l'hash della riga scritta."""
        prev_hash = self._last_hash()

        # record.dict() ordinato + default=str per Enum/UUID/datetime
        payload = json.loads(record.model_dump_json())
        record_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)

        this_hash = _record_hash(prev_hash, record_json)

        line = {
            "_prev_hash": prev_hash,
            "_hash": this_hash,
            "record": payload,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

        return this_hash

    def read_all(self) -> list[dict[str, Any]]:
        entries = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def verify_integrity(self) -> tuple[bool, str | None]:
        """Ricalcola la catena di hash dall'inizio. Ritorna (True, None) se
        tutto torna, altrimenti (False, motivo) al primo punto di rottura."""
        prev_hash = GENESIS_HASH
        for i, entry in enumerate(self.read_all()):
            if entry["_prev_hash"] != prev_hash:
                return False, f"Riga {i}: prev_hash non combacia (log alterato o riordinato)"

            record_json = json.dumps(entry["record"], sort_keys=True, ensure_ascii=False)
            expected_hash = _record_hash(prev_hash, record_json)
            if entry["_hash"] != expected_hash:
                return False, f"Riga {i}: hash non combacia con il contenuto (record modificato)"

            prev_hash = entry["_hash"]

        return True, None
