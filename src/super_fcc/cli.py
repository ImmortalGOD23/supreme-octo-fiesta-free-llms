"""Small local orchestrator; provider inference remains owned by FCC."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = {
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "cliproxyapi": "http://127.0.0.1:8317/v1",
    "9router": "http://127.0.0.1:20128/v1",
    "freellmapi": "http://127.0.0.1:3001/v1",
}
NVIDIA_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "minimaxai/minimax-m3.1-flash",
    "z-ai/glm-5.3-flash",
]


def private_write(path, text):
    """Atomic replacement with private permissions, including on existing files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def uv_command(*args):
    if not shutil.which("uv"):
        raise ValueError("Instale uv: https://docs.astral.sh/uv/getting-started/installation/")
    # Bootstrap the exact compatible uv without replacing the user's system binary.
    return ["uv", "tool", "run", "--from", "uv==0.13.7", "uv", "run", "--frozen", "--no-dev",
            "--project", str(ROOT / "upstream/fcc"), *args]


def init_workspace():
    runtime = ROOT / ".runtime"
    if (runtime / "stack.env").exists():
        print("Configuração existente preservada.")
        return
    runtime.mkdir(exist_ok=True, mode=0o700)
    key = secrets.token_urlsafe(32)
    management = secrets.token_urlsafe(32)
    private_write(runtime / "stack.env", "\n".join([
        "NINEROUTER_PASSWORD=" + secrets.token_urlsafe(24),
        "NINEROUTER_JWT=" + secrets.token_hex(32),
        "NINEROUTER_API_SECRET=" + secrets.token_hex(32),
        "FREELLMAPI_ENCRYPTION_KEY=" + secrets.token_hex(32), "",
    ]))
    config = {
        "config-version": 8,
        "server": {"host": "0.0.0.0", "port": 8317},
        "management": {"allow-remote": False, "secret-key": management},
        "access": {"api-keys": [key]},
        "oauth": {"auth-dir": "/root/.cli-proxy-api"},
        "routing": {"strategy": "round-robin"},
    }
    # JSON is a YAML subset; the pinned CLIProxyAPI YAML decoder accepts it.
    private_write(runtime / "cliproxyapi.yaml", json.dumps(config, indent=2) + "\n")
    private_write(runtime / "cliproxyapi.key", key + "\n")
    private_write(runtime / "cliproxyapi-management.key", management + "\n")
    (runtime / "cliproxyapi-auth").mkdir(exist_ok=True, mode=0o700)
    print("Segredos locais criados em .runtime/ (ignorados pelo Git).")


def models(provider, key):
    headers = {"Authorization": "Bearer " + key} if key else {}
    request = urllib.request.Request(ENDPOINTS[provider] + "/models", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        identifiers = sorted({row["id"] for row in data["data"] if isinstance(row.get("id"), str)})
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        raise ValueError(f"{provider}: HTTP {code}; confira chave, login e serviço.") from None
    except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError):
        raise ValueError(f"Não foi possível obter o catálogo de {provider}.") from None
    return identifiers


def provider_key(provider):
    if provider == "nvidia" and os.environ.get("NVIDIA_API_KEY"):
        return os.environ["NVIDIA_API_KEY"].strip()
    if provider == "cliproxyapi":
        path = ROOT / ".runtime/cliproxyapi.key"
        if path.exists():
            return path.read_text().strip()
    return getpass.getpass(f"Chave de {provider} (entrada oculta): ").strip()


def configure_nvidia():
    key = provider_key("nvidia")
    if not key:
        raise ValueError("Uma chave NVIDIA é necessária.")
    available = models("nvidia", key)
    missing = [model for model in NVIDIA_MODELS if model not in available]
    if missing:
        raise ValueError("Modelos ausentes no catálogo atual: " + ", ".join(missing)
                         + ". Use 'models nvidia' e configure os disponíveis no Admin do FCC.")
    payload = {
        "operation": "nvidia",
        "settings": {
            "NVIDIA_NIM_API_KEY": json.dumps([key]),
            "HOST": "127.0.0.1",
            "MODEL": "nvidia_nim/" + NVIDIA_MODELS[0],
            "MODEL_FALLBACKS": json.dumps([
                {"model": "nvidia_nim/" + model, "reasoning": "inherit", "api_key_number": 1}
                for model in NVIDIA_MODELS[1:]
            ]),
        },
    }
    apply_fcc(payload)


def apply_fcc(payload):
    """Pass secrets over stdin, never argv or tracked configuration."""
    command = uv_command("python", str(ROOT / "scripts/fcc_config.py"))
    subprocess.run(command, input=json.dumps(payload), text=True, cwd=ROOT, check=True)


def connect(provider, model, use_as):
    key = provider_key(provider)
    available = models(provider, key)
    if model not in available:
        raise ValueError("Modelo ausente. Consulte 'models " + provider + "' antes de conectar.")
    definition = {
        "provider_id": "custom_" + uuid.uuid5(uuid.NAMESPACE_URL, ENDPOINTS[provider]).hex,
        "display_name": "Super FCC / " + provider,
        "base_url": ENDPOINTS[provider],
        "api_keys": [key] if key else [],
        "api_format": "openai_chat",
        "reasoning_format": "provider_default",
        "model_ids": [],
    }
    apply_fcc({"operation": "connect", "provider": definition, "model": model, "use_as": use_as})


def compose(action, services):
    if not (ROOT / ".runtime/stack.env").exists():
        raise ValueError("Execute 'init' primeiro.")
    command = ["docker", "compose", "--env-file", str(ROOT / ".runtime/stack.env"),
               "-f", str(ROOT / "compose.yaml")]
    if action == "up":
        command += ["up", "--build", "-d", *services]
    elif action == "stop":
        command += ["stop", *services]
    else:
        command += ["logs", "--tail", "80", *services]
    run(command)


def doctor():
    good = True
    lock = json.loads((ROOT / "upstreams.lock.json").read_text())
    for name, entry in lock.items():
        path = ROOT / "upstream" / name
        result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                                capture_output=True, text=True)
        ok = result.returncode == 0 and result.stdout.strip() == entry["commit"]
        good &= ok
        print(f"{'OK' if ok else 'FALHA'} upstream/{name}")
    for tool in ["uv", "docker", "git"]:
        ok = bool(shutil.which(tool))
        good &= ok
        print(f"{'OK' if ok else 'FALHA'} {tool}")
    print("NVIDIA e integrações exigem suas chaves; nenhum teste de inferência foi executado.")
    return good


def main():
    parser = argparse.ArgumentParser(description="Super FCC — núcleo FCC, gateways opcionais")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["init", "doctor", "install-fcc", "configure-nvidia", "serve", "catalog"]:
        commands.add_parser(name)
    launch = commands.add_parser("agent")
    launch.add_argument("name", choices=["claude", "codex", "opencode", "hermes", "pi", "aider"])
    listing = commands.add_parser("models")
    listing.add_argument("provider", choices=ENDPOINTS)
    connection = commands.add_parser("connect")
    connection.add_argument("provider", choices=["cliproxyapi", "9router", "freellmapi"])
    connection.add_argument("model", help="ID exato retornado pelo gateway")
    connection.add_argument("--use-as", choices=["available", "default", "fallback"], default="available")
    for action in ["up", "stop", "logs"]:
        cmd = commands.add_parser(action)
        cmd.add_argument("services", nargs="+", choices=["cliproxyapi", "9router", "freellmapi"])
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_workspace()
        elif args.command == "doctor":
            if not doctor():
                raise SystemExit(1)
        elif args.command == "install-fcc":
            run(uv_command("python", "-c", "print('FCC instalado; configure o provedor e execute serve.')"))
        elif args.command == "configure-nvidia":
            configure_nvidia()
        elif args.command == "serve":
            run(uv_command("fcc-server"))
        elif args.command == "agent":
            # Preserve the caller's coding project directory.
            subprocess.run(uv_command("fcc-" + args.name), check=True)
        elif args.command == "models":
            print("\n".join(models(args.provider, provider_key(args.provider))))
        elif args.command == "connect":
            connect(args.provider, args.model, args.use_as)
        elif args.command == "catalog":
            print(ROOT / "upstream/free-llm/README.md")
            print("https://free-llm.com — catálogo de referência; confirme cotas com cada provedor.")
        elif args.command in {"up", "stop", "logs"}:
            compose(args.command, args.services)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # Never stringify exceptions from upstream validators: inputs can contain secrets.
        if isinstance(error, ValueError):
            print(str(error), file=sys.stderr)
        else:
            print("Comando falhou. Confira dependências e mensagens do processo acima.", file=sys.stderr)
        raise SystemExit(1) from None
