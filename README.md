# Aurelius Protocol

A Bittensor subnet for moral reasoning alignment. Miners submit structured ethical-dilemma
scenario configurations; validators score them through an 8-stage pipeline and run
accepted scenarios through [Concordia](https://github.com/google-deepmind/concordia)
generative-agent simulations. The resulting transcripts form training data that improves
LLM performance on moral reasoning benchmarks (MoReBench).

> **This is the `testnet` branch.** It tracks the v3 codebase and publishes
> `:testnet`-tagged images to public GHCR on every push. For mainnet, see
> [Mainnet](#mainnet).

| | |
|---|---|
| Testnet subnet | `netuid 455` on the Bittensor `test` network |
| Validator image | `ghcr.io/aurelius-protocol/aurelius-validator:testnet` |
| Miner image | `ghcr.io/aurelius-protocol/aurelius-miner:testnet` |
| Simulation image | `ghcr.io/aurelius-protocol/aurelius-concordia:testnet` (pulled automatically by validators) |
| GHCR auth | Not required — images are public |

---

## Quickstart — Testnet Validator

Three commands. Prerequisites:

- Docker 20.10+
- A Bittensor wallet registered on testnet `netuid 455`
  (`btcli subnet register --netuid 455 --network test`)
- An OpenAI-compatible LLM API key — [DeepSeek](https://platform.deepseek.com/) is the
  default and cheapest; OpenAI / Anthropic also work

```bash
# 1. Pull the latest testnet image
docker pull ghcr.io/aurelius-protocol/aurelius-validator:testnet

# 2. Write a minimal .env — ENVIRONMENT=testnet auto-sets netuid, network,
#    Central API URL, simulation resources, and safety flags.
cat > .env <<'EOF'
ENVIRONMENT=testnet
WALLET_NAME=your-wallet
WALLET_HOTKEY=your-hotkey
LLM_API_KEY=sk-...
EOF

# 3. Run. Validators need Docker daemon access to spawn sandboxed simulation
#    containers — hence the /var/run/docker.sock mount.
mkdir -p data simdata
docker run -d \
  --name aurelius-validator \
  --restart unless-stopped \
  --env-file .env \
  -v ~/.bittensor/wallets:/home/appuser/.bittensor/wallets:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/simdata:/sim-data" \
  ghcr.io/aurelius-protocol/aurelius-validator:testnet

docker logs -f aurelius-validator
```

For stricter production isolation, use the `docker-socket-proxy` setup in
[Production Setup](#production-setup-docker-compose) instead of the raw socket mount.

---

## Quickstart — Testnet Miner

Prerequisites:

- Docker 20.10+
- A Bittensor wallet registered on testnet `netuid 455`
- A publicly reachable IP and an open inbound TCP port for the axon (default `8091`)

```bash
# 1. Pull the latest testnet image
docker pull ghcr.io/aurelius-protocol/aurelius-miner:testnet

# 2. Write a minimal .env
cat > .env <<'EOF'
ENVIRONMENT=testnet
WALLET_NAME=your-wallet
WALLET_HOTKEY=your-hotkey
AXON_EXTERNAL_IP=<your-public-ip>
AXON_EXTERNAL_PORT=8091
EOF

# 3. Run
mkdir -p data
docker run -d \
  --name aurelius-miner \
  --restart unless-stopped \
  --env-file .env \
  -p 8091:8091 \
  -v ~/.bittensor/wallets:/home/appuser/.bittensor/wallets:ro \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/aurelius-protocol/aurelius-miner:testnet

docker logs -f aurelius-miner
```

---

## How It Works

```
Miner                      Validator                       Central API
  |                            |                                |
  |   ScenarioConfigSynapse    |                                |
  |--------------------------->|                                |
  |   (scenario_config,        |  1. version check              |
  |    work_id, signature)     |  2. schema validation          |
  |                            |  3. work-token balance ------->|
  |                            |  4. rate-limit (per hotkey)    |
  |                            |  5. novelty check (FAISS)      |
  |                            |  6. classifier quality gate    |
  |                            |  7. Concordia simulation       |
  |                            |     (sandboxed container)      |
  |                            |  8. work-token deduct -------->|
  |                            |     + on-chain weight set      |
  |                            |  report submission ----------->|
```

The pipeline short-circuits on the first failure and only deducts the work-token after
all eight stages pass. The Concordia simulation runs in an ephemeral container with
CPU/RAM limits scaled to the scenario's agent count, and its LLM egress is firewalled to
the allowlist in `SIM_ALLOWED_LLM_HOSTS`. Transcripts are parsed, scored for coherence,
and become the payload that determines the miner's on-chain weight.

Code landmarks: wire format in [`aurelius/protocol.py`](aurelius/protocol.py), pipeline
in [`aurelius/validator/pipeline.py`](aurelius/validator/pipeline.py), simulation runner
in [`aurelius/simulation/docker_runner.py`](aurelius/simulation/docker_runner.py).

---

## Configuration

Setting `ENVIRONMENT` selects a profile and auto-configures subnet, network, Central API
URL, simulation resources, and safety flags. The six variables below cover nearly every
operator deployment:

| Variable | Required for | Purpose | Default |
|---|---|---|---|
| `ENVIRONMENT` | both | `local` \| `testnet` \| `mainnet` — selects profile | `local` |
| `WALLET_NAME` | both | Bittensor coldkey wallet name | `default` |
| `WALLET_HOTKEY` | both | Bittensor hotkey name | `default` |
| `LLM_API_KEY` | validator | OpenAI-compatible LLM key for Concordia | (empty) |
| `LLM_BASE_URL` | validator (opt.) | Override LLM endpoint | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | validator (opt.) | Override model name | `deepseek-chat` |
| `AXON_EXTERNAL_IP` | miner | Public IP the miner advertises | (empty → use local IP) |
| `AXON_EXTERNAL_PORT` | miner | Public port the miner advertises | `8091` |

See [`.env.example`](.env.example) for the full surface and
[`aurelius/config.py`](aurelius/config.py) for the authoritative defaults per profile.

**Two-tier config model.** The list above is the *local* tier (wallet, network, secrets —
set at startup, never changes). A *remote* tier (polling interval, classifier threshold,
novelty threshold, rate limits, minimum protocol versions) is fetched from the Central
API at runtime, cached for 5 minutes, and refreshed transparently. Operators do not set
any of the remote-tier values — they live server-side.

---

## Production Setup (Docker Compose)

More robust than `docker run`: adds a `docker-socket-proxy` sidecar so the validator
never touches the Docker daemon directly, plus watchtower for auto-update on every push
to the `testnet` branch.

```yaml
# docker-compose.yml
services:
  aurelius-validator:
    image: ghcr.io/aurelius-protocol/aurelius-validator:testnet
    container_name: aurelius-validator
    restart: unless-stopped
    env_file: .env
    environment:
      DOCKER_HOST: tcp://docker-proxy:2375
    volumes:
      - ~/.bittensor/wallets:/home/appuser/.bittensor/wallets:ro
      - ./data:/app/data
      - ./simdata:/sim-data
    depends_on:
      - docker-proxy
    labels:
      com.centurylinklabs.watchtower.enable: "true"

  docker-proxy:
    image: tecnativa/docker-socket-proxy:0.3.0
    container_name: docker-proxy
    restart: unless-stopped
    environment:
      CONTAINERS: 1
      IMAGES: 1
      POST: 1
      NETWORKS: 1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    environment:
      WATCHTOWER_CLEANUP: "true"
      WATCHTOWER_POLL_INTERVAL: "300"
      WATCHTOWER_LABEL_ENABLE: "true"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    labels:
      com.centurylinklabs.watchtower.enable: "true"
```

Bring it up with `docker compose up -d`. Watchtower polls GHCR every 5 minutes and
rolls the validator forward whenever the `:testnet` tag is updated. Because GHCR packages
under `aurelius-protocol` are public, no registry credentials are mounted.

Miners can use a simpler compose (no proxy, no sim-data) if they prefer compose over
`docker run`.

---

## Running From Source

For development, or if you prefer not to use Docker:

```bash
git clone https://github.com/Aurelius-Protocol/Aurelius-Protocol.git
cd Aurelius-Protocol
git checkout testnet

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[ml,simulation]"   # validator + miner runtime deps

cp .env.example .env
$EDITOR .env                         # fill in ENVIRONMENT, wallet, etc.

aurelius-validator                   # or: aurelius-miner
```

Extras: `[ml]` for embeddings/classifier, `[simulation]` for the Concordia Docker SDK,
`[benchmark]` for fine-tuning / MoReBench evaluation, `[dev]` for pytest and ruff.
`aurelius-deposit` is a one-shot CLI for verifying coldkey deposits.

---

## Development & Testing

```bash
pip install -e ".[ml,simulation,dev]"

# Fast tests — no network, no Docker
pytest tests/ --ignore=tests/e2e --ignore=tests/common/test_embeddings.py

# Full suite including Docker-dependent simulation tests
pytest tests/

# E2E (requires a running testnet and a funded wallet)
pytest tests/e2e/ -m e2e

# Lint / format
ruff check aurelius/
ruff format aurelius/
```

---

## Security Notes

- **Concordia isolation.** Every simulation runs in an ephemeral Docker container with
  capped RAM / CPU, egress limited to `SIM_ALLOWED_LLM_HOSTS`, and no persistent
  filesystem outside the mounted `/sim-data`.
- **Socket proxy.** The raw `/var/run/docker.sock` mount in the quickstart is fine for
  testnet exploration but exposes full Docker API access. Prefer the
  `tecnativa/docker-socket-proxy` setup from [Production Setup](#production-setup-docker-compose)
  for anything long-lived.
- **Image digest pinning.** `REQUIRE_IMAGE_DIGEST=1` is on by default in the testnet and
  mainnet profiles. The Concordia image digest is auto-pinned by CI after each build,
  so operators don't need to configure `CONCORDIA_IMAGE_DIGEST` themselves — just keep
  your validator image current.
- **Work-token accounting.** Balance is checked in stage 3 but deducted only in stage 8,
  after successful simulation. Fail-closed behavior: if the Central API is unreachable
  during balance check, submissions are rejected rather than admitted for free.

---

## Mainnet

Mainnet operation uses `ENVIRONMENT=mainnet` (netuid 37, `finney` network) and images
tagged `:latest`. The v2→v3 cutover is in progress; until it ships, `:latest` on GHCR
still holds the legacy v2 code published from `main`. This README covers v3 only —
follow the repository's releases page for the cutover schedule.

---

## Links

- [Bittensor docs](https://docs.bittensor.com)
- [Subnet 455 on taostats (testnet)](https://taostats.io/subnet/455/)
- [GHCR packages](https://github.com/orgs/Aurelius-Protocol/packages)
- [Issues](https://github.com/Aurelius-Protocol/Aurelius-Protocol/issues)

## License

MIT
