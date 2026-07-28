# WALLET_BALANCE_CHECKER

**Beschreibung**: CLI-Tool zum Abfragen von ETH/SOL Kontoständen und Transaktionen von hinterlegten Adressen.

---

## A. Sollzustand

Ein einfaches Python-Skript, das:
1. Eine vorgegebene Wallet-Adresse (ETH oder SOL) akzeptiert
2. Den aktuellen Kontostand abfragt (via RPC / Blockchain-API)
3. Die letzten N Transaktionen listet
4. Optional: Transaktionen an andere vorgegebene Adressen senden kann

---

## B. Health Check & UI

**Projekt-Typ**: CLI-Tool

**Implementierung**: Python (mit web3.py für ETH, solana für SOL)

Zu Beginn prüft das Skript die RPC-Verbindung (gemäß `.env`). Klappt das, zeigt es einen grünen ✔️ und ist ready. Schlägt der Health-Check fehl, gibt es einen roten Hinweis + Exitcode.

**Features**:
- `python balance.py --address <wallet_address>` → zeigt Kontostand (ETH oder SOL)
- `python balance.py --address <wallet_address> --tx-count 10` → zeigt letzte 10 Transaktionen
- `python balance.py --send <recipient_address> <amount>` → sendet Coins an vorgegebene Adresse (mit Sicherheits-Prompt)
- `python balance.py --help` → Dokumentation

**Standardverhalten**: Ohne Argumente zeigt Health-Check an und listet verfügbare Commands.

---

## C. Setup & Dependencies

### Python venv
```bash
python3.10 -m venv venv
source venv/bin/activate
```

### Pip Packages
```bash
pip install web3          # Ethereum
pip install solders       # Solana
pip install solana        # Solana Client
pip install python-dotenv # .env Secrets
pip install requests      # HTTP Calls
```

### requirements.txt
```
web3==6.11.0
solders==0.20.0
solana==0.31.0
python-dotenv==1.0.0
requests==2.31.0
```

---

## C.5 Code-Beispiel (ETH)

```python
from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()
RPC_URL = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

address = "0x1234..."
balance_wei = w3.eth.get_balance(address)
balance_eth = Web3.from_wei(balance_wei, 'ether')
print(f"Balance: {balance_eth} ETH")
```

### Code-Beispiel (SOL)

```python
from solana.rpc.api import Client
from solana.publickey import PublicKey
from dotenv import load_dotenv
import os

load_dotenv()
SOL_RPC_URL = os.getenv("SOL_RPC_URL", "https://api.mainnet-beta.solana.com")
client = Client(SOL_RPC_URL)

pubkey = PublicKey("...")
balance = client.get_balance(pubkey)
print(f"Balance: {balance['result']['value'] / 1e9} SOL")
```

---

## D. Artefakte, Dateien & Libraries

- `balance.py` – Hauptskript
- `.env` – Secrets (RPC URLs, Private Keys)
- `config.toml` – Netzwerk-Parameter
- `requirements.txt` – Dependencies

### .env Beispiel

```
ETH_RPC_URL=https://eth.llamarpc.com
SOL_RPC_URL=https://api.mainnet-beta.solana.com
WALLET_PRIVATE_KEY=your_secret_key_here
```

### config.toml Beispiel

```toml
[ethereum]
network = "mainnet"
rpc_url = "https://eth.llamarpc.com"
chain_id = 1

[solana]
network = "mainnet-beta"
rpc_url = "https://api.mainnet-beta.solana.com"
```

---

## E. Peripherie

- Unterstützt Ethereum (ETH) & Solana (SOL) Netzwerke
- RPC-Endpoints über `.env` konfigurierbar
- Private Key nur in `.env`, niemals im Code
- Optional: Transaktions-Signing für Sends (mit Sicherheits-Prompt)

---

## F. Ideen & Weiteres

- Multi-Wallet Support (mehrere Adressen auf einmal abfragen)?
- Portfolio-Tracking (Preise in USD anzeigen)?
- Automatische Notifikationen wenn TX eingeht?
- Web-Dashboard statt CLI?
- Unterstützung für andere Chains (Polygon, Arbitrum, etc.)?

