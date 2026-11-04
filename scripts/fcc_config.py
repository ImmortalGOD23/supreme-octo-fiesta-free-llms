"""Run using the pinned FCC environment; merge through its validated config store."""
import json
import os
from pathlib import Path
import sys
import time

from free_claude_code.config.loader import ManagedConfigStore, compose_settings_snapshot


def apply(payload):
    store = ManagedConfigStore()
    store.initialize()
    before = store.read()
    values = dict(before.managed)
    if payload["operation"] == "nvidia":
        # Preserve every existing NVIDIA key; a newly supplied key becomes Key 1.
        from free_claude_code.config.api_keys import api_key_values
        supplied = json.loads(payload["settings"]["NVIDIA_NIM_API_KEY"])
        existing = api_key_values(before.settings.nvidia_nim_api_keys)
        updates = dict(payload["settings"])
        updates["NVIDIA_NIM_API_KEY"] = json.dumps(list(dict.fromkeys(supplied + existing)))
        values.update(updates)
        # Make the new default effective for every tier.
        for key in ["MODEL_FABLE", "MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU"]:
            values.pop(key, None)
        changed = set(updates) | {"MODEL_FABLE", "MODEL_OPUS", "MODEL_SONNET", "MODEL_HAIKU"}
    elif payload["operation"] == "connect":
        definition = payload["provider"]
        providers = [item.private_values() for item in before.settings.custom_providers
                     if item.provider_id != definition["provider_id"]]
        providers.append(definition)
        values["FCC_CUSTOM_PROVIDERS"] = json.dumps(providers)
        changed = {"FCC_CUSTOM_PROVIDERS"}
        ref = definition["provider_id"] + "/" + payload["model"]
        if payload["use_as"] == "default":
            values["MODEL"] = ref
            changed.add("MODEL")
        elif payload["use_as"] == "fallback":
            fallbacks = [item.model_dump(mode="json") for item in before.settings.model_fallbacks or ()]
            if not any(item["model"] == ref for item in fallbacks):
                fallbacks.append({"model": ref, "reasoning": "inherit", "api_key_number": 1})
            values["MODEL_FALLBACKS"] = json.dumps(fallbacks)
            changed.add("MODEL_FALLBACKS")
    else:
        raise ValueError("Operação desconhecida")
    if changed & set(before.process):
        raise ValueError("Há overrides no ambiente. Remova-os antes de aplicar pelo Super FCC.")
    compose_settings_snapshot(values, dict(os.environ))
    backup = Path(str(store.path) + f".super-fcc-{time.time_ns()}.bak")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(store.path.read_bytes())
    store.commit(values, expected=before)
    print("Configuração FCC validada e aplicada. Backup privado: " + str(backup))
    print("Reinicie o servidor FCC e abra uma nova sessão do agente.")


if __name__ == "__main__":
    try:
        apply(json.load(sys.stdin))
    except Exception:
        print("Configuração não aplicada. Confira o schema FCC, overrides e disponibilidade do arquivo.", file=sys.stderr)
        sys.exit(1)
