#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Babalon — CLI and client for the WizardFinance on-chain advice and investment platform.
Register as advisor, create portfolios, deposit/withdraw, view stats and client tiers.
Usage:
  python babalon_app.py config [--rpc-url URL] [--contract 0x...] [--save]
  python babalon_app.py register-advisor --rpc-url URL --private-key KEY --contract 0x...
  python babalon_app.py create-portfolio --rpc-url URL --private-key KEY --contract 0x... --advisor-id N
  python babalon_app.py deposit --rpc-url URL --private-key KEY --contract 0x... --portfolio-id N [--token 0x...] --amount-wei W
  python babalon_app.py withdraw --rpc-url URL --private-key KEY --contract 0x... --portfolio-id N [--token 0x...] --amount-wei W
  python babalon_app.py close-portfolio --rpc-url URL --private-key KEY --contract 0x... --portfolio-id N
  python babalon_app.py list-advisors --rpc-url URL --contract 0x... [--limit N]
  python babalon_app.py list-portfolios --rpc-url URL --contract 0x... [--limit N]
  python babalon_app.py stats --rpc-url URL --contract 0x...
  python babalon_app.py client-stats --rpc-url URL --contract 0x... --address 0x...
  python babalon_app.py portfolio-info --rpc-url URL --contract 0x... --portfolio-id N
  python babalon_app.py advisor-info --rpc-url URL --contract 0x... --advisor-id N
  python babalon_app.py constants | tier-names | fee-calc | version | demo | interactive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

APP_NAME = "Babalon"
BABALON_VERSION = "1.0.0"
CONTRACT_NAME = "WizardFinance"
CONFIG_DIR = ".babalon"
CONFIG_FILE = "config.json"
DEFAULT_RPC_URL = os.environ.get("BABALON_RPC_URL", "http://127.0.0.1:8545")
DEFAULT_CONTRACT = os.environ.get("BABALON_CONTRACT", "")

# Tier labels (WizardFinance: 0=None, 1=Bronze, 2=Silver, 3=Gold, 4=Platinum)
BABALON_TIER_NAMES = {0: "None", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum"}
BABALON_TIER_MIN_WEI = {
    1: 100000000000000000,   # 0.1 ether
    2: 1000000000000000000,  # 1 ether
    3: 10000000000000000000, # 10 ether
    4: 100000000000000000000, # 100 ether
}

# Minimal ABI for WizardFinance (view + state-changing)
WIZARDFINANCE_ABI = [
    {"inputs": [], "name": "registerAdvisor", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "advisorId", "type": "uint256"}], "name": "createPortfolio", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "portfolioId", "type": "uint256"}, {"internalType": "address", "name": "token", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "portfolioId", "type": "uint256"}, {"internalType": "address", "name": "token", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "portfolioId", "type": "uint256"}], "name": "closePortfolio", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "portfolioId", "type": "uint256"}], "name": "getPortfolio", "outputs": [{"internalType": "address", "name": "client_", "type": "address"}, {"internalType": "uint256", "name": "advisorId_", "type": "uint256"}, {"internalType": "uint256", "name": "totalDeposited_", "type": "uint256"}, {"internalType": "uint256", "name": "totalWithdrawn_", "type": "uint256"}, {"internalType": "uint256", "name": "createdAtBlock_", "type": "uint256"}, {"internalType": "bool", "name": "closed_", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "advisorId", "type": "uint256"}], "name": "getAdvisor", "outputs": [{"internalType": "address", "name": "wallet_", "type": "address"}, {"internalType": "bool", "name": "active_", "type": "bool"}, {"internalType": "uint256", "name": "totalClients_", "type": "uint256"}, {"internalType": "uint256", "name": "totalFeesEarned_", "type": "uint256"}, {"internalType": "uint256", "name": "registeredAtBlock_", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getGlobalStats", "outputs": [{"internalType": "uint256", "name": "totalDeposits_", "type": "uint256"}, {"internalType": "uint256", "name": "totalWithdrawn_", "type": "uint256"}, {"internalType": "uint256", "name": "totalFeesCollected_", "type": "uint256"}, {"internalType": "uint256", "name": "advisorCount_", "type": "uint256"}, {"internalType": "uint256", "name": "portfolioCount_", "type": "uint256"}, {"internalType": "bool", "name": "paused_", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "client", "type": "address"}], "name": "getClientPortfolioIds", "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "portfolioId", "type": "uint256"}, {"internalType": "address", "name": "token", "type": "address"}], "name": "getPortfolioBalance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "advisorCount", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "portfolioCount", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "client", "type": "address"}], "name": "getClientTier", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "wallet", "type": "address"}], "name": "getAdvisorId", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "wfPaused", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WF_MIN_DEPOSIT", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WF_MAX_DEPOSIT_SINGLE", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WF_ADVISOR_FEE_BPS", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WF_PLATFORM_FEE_BPS", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WF_BPS", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

# -----------------------------------------------------------------------------
# Config load / save
# -----------------------------------------------------------------------------

def config_path() -> Path:
    return Path.home() / CONFIG_DIR / CONFIG_FILE

def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {"rpc_url": DEFAULT_RPC_URL, "contract": DEFAULT_CONTRACT}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"rpc_url": DEFAULT_RPC_URL, "contract": DEFAULT_CONTRACT}

def save_config(rpc_url: str, contract: str) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"rpc_url": rpc_url, "contract": contract}, f, indent=2)

# -----------------------------------------------------------------------------
# Web3 helpers
# -----------------------------------------------------------------------------

def get_w3(rpc_url: str):
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise RuntimeError("Not connected to RPC")
        return w3
    except ImportError:
        raise RuntimeError("Install web3: pip install web3")

def get_contract(w3, address: str):
    from web3 import Web3
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=WIZARDFINANCE_ABI)

def get_signer_account(w3, private_key: str):
    from web3 import Web3
    pk = private_key.strip()
    if pk.startswith("0x"):
        pk = pk[2:]
    return w3.eth.account.from_key(pk)

def normalize_address(addr: str) -> str:
    from web3 import Web3
    return Web3.to_checksum_address(addr)

def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"

# -----------------------------------------------------------------------------
# Formatting and display
# -----------------------------------------------------------------------------

def wei_to_ether(wei: int) -> float:
    return wei / 1e18

def ether_to_wei(eth: float) -> int:
    return int(eth * 1e18)

def format_wei(wei: int) -> str:
    return f"{wei_to_ether(wei):.6f} ETH"

def tier_name(tier: int) -> str:
    return BABALON_TIER_NAMES.get(tier, "Unknown")

def format_portfolio_line(portfolio_id: int, client: str, advisor_id: int, deposited: int, withdrawn: int, closed: bool) -> str:
    net = deposited - withdrawn
    status = "closed" if closed else "open"
    return f"  Portfolio #{portfolio_id}  client={client[:10]}...  advisor={advisor_id}  deposited={format_wei(deposited)}  withdrawn={format_wei(withdrawn)}  net={format_wei(net)}  [{status}]"

def format_advisor_line(advisor_id: int, wallet: str, active: bool, clients: int, fees: int) -> str:
    act = "active" if active else "inactive"
    return f"  Advisor #{advisor_id}  wallet={wallet[:10]}...  {act}  clients={clients}  fees_earned={format_wei(fees)}"

# -----------------------------------------------------------------------------
# Fee calculation (local mirror of contract BPS)
# -----------------------------------------------------------------------------

BPS = 10000
ADVISOR_FEE_BPS = 200
PLATFORM_FEE_BPS = 50

def compute_advisor_fee(amount_wei: int) -> int:
    return (amount_wei * ADVISOR_FEE_BPS) // BPS

def compute_platform_fee(amount_wei: int) -> int:
    return (amount_wei * PLATFORM_FEE_BPS) // BPS

def compute_total_fee(amount_wei: int) -> int:
    return compute_advisor_fee(amount_wei) + compute_platform_fee(amount_wei)

def compute_net_after_fees(amount_wei: int) -> int:
    return amount_wei - compute_total_fee(amount_wei)

def fee_breakdown(amount_wei: int) -> Tuple[int, int, int]:
    adv = compute_advisor_fee(amount_wei)
    plat = compute_platform_fee(amount_wei)
    net = amount_wei - adv - plat
    return (adv, plat, net)

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

def parse_wei(s: str) -> int:
    s = s.strip()
    if s.startswith("0x"):
        return int(s, 16)
    return int(s)

def validate_address(s: str) -> str:
    s = s.strip()
    if not s.startswith("0x"):
        s = "0x" + s
    if len(s) != 42:
        raise ValueError("Address must be 40 hex chars after 0x")
    return normalize_address(s)

def validate_portfolio_id(n: int) -> None:
    if n < 1:
        raise ValueError("portfolio_id must be >= 1")

def validate_advisor_id(n: int) -> None:
    if n < 1:
        raise ValueError("advisor_id must be >= 1")

# -----------------------------------------------------------------------------
# Commands: config
# -----------------------------------------------------------------------------

def cmd_config(args: argparse.Namespace) -> int:
    cfg = load_config()
    rpc = getattr(args, "rpc_url", None) or cfg.get("rpc_url", DEFAULT_RPC_URL)
    contract = getattr(args, "contract", None) or cfg.get("contract", DEFAULT_CONTRACT)
    print("RPC URL:", rpc)
    print("Contract:", contract or "(not set)")
    if getattr(args, "save", False):
        save_config(rpc, contract)
        print("Saved to", config_path())
    return 0

# -----------------------------------------------------------------------------
# Commands: register-advisor
# -----------------------------------------------------------------------------

def cmd_register_advisor(args: argparse.Namespace) -> int:
    rpc = args.rpc_url or load_config().get("rpc_url", DEFAULT_RPC_URL)
    contract_addr = args.contract or load_config().get("contract", DEFAULT_CONTRACT)
    if not contract_addr:
        print("Error: --contract or config required", file=sys.stderr)
        return 1
    pk = getattr(args, "private_key", None)
    if not pk:
        print("Error: --private-key required", file=sys.stderr)
        return 1
    try:
        w3 = get_w3(rpc)
        acct = get_signer_account(w3, pk)
        contract = get_contract(w3, contract_addr)
        tx = contract.functions.registerAdvisor().build_transaction({
            "from": acct.address,
            "gas": 200000,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt["status"] != 1:
            print("Transaction failed", file=sys.stderr)
            return 1
        advisor_id = contract.functions.getAdvisorId(acct.address).call()
        print("Advisor registered. Advisor ID:", advisor_id)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 1
    return 0

# -----------------------------------------------------------------------------
# Commands: create-portfolio
# -----------------------------------------------------------------------------

def cmd_create_portfolio(args: argparse.Namespace) -> int:
    rpc = args.rpc_url or load_config().get("rpc_url", DEFAULT_RPC_URL)
    contract_addr = args.contract or load_config().get("contract", DEFAULT_CONTRACT)
    if not contract_addr:
        print("Error: --contract or config required", file=sys.stderr)
        return 1
    pk = getattr(args, "private_key", None)
    if not pk:
        print("Error: --private-key required", file=sys.stderr)
        return 1
    advisor_id = getattr(args, "advisor_id", None)
    if advisor_id is None:
        print("Error: --advisor-id required", file=sys.stderr)
        return 1
    try:
        validate_advisor_id(int(advisor_id))
        w3 = get_w3(rpc)
        acct = get_signer_account(w3, pk)
        contract = get_contract(w3, contract_addr)
        tx = contract.functions.createPortfolio(int(advisor_id)).build_transaction({
            "from": acct.address,
            "gas": 200000,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt["status"] != 1:
            print("Transaction failed", file=sys.stderr)
            return 1
        portfolio_count = contract.functions.portfolioCount().call()
        print("Portfolio created. Portfolio ID:", portfolio_count)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 1
    return 0

# -----------------------------------------------------------------------------
# Commands: deposit
# -----------------------------------------------------------------------------

def cmd_deposit(args: argparse.Namespace) -> int:
    rpc = args.rpc_url or load_config().get("rpc_url", DEFAULT_RPC_URL)
    contract_addr = args.contract or load_config().get("contract", DEFAULT_CONTRACT)
    if not contract_addr:
        print("Error: --contract or config required", file=sys.stderr)
        return 1
    pk = getattr(args, "private_key", None)
    if not pk:
        print("Error: --private-key required", file=sys.stderr)
        return 1
    portfolio_id = getattr(args, "portfolio_id", None)
    amount_wei = getattr(args, "amount_wei", None)
    if portfolio_id is None or amount_wei is None:
        print("Error: --portfolio-id and --amount-wei required", file=sys.stderr)
        return 1
    token = getattr(args, "token", None) or zero_address()
    try:
        portfolio_id = int(portfolio_id)
        amount_wei = parse_wei(str(amount_wei))
        if token != zero_address():
            token = validate_address(token)
        validate_portfolio_id(portfolio_id)
        w3 = get_w3(rpc)
        acct = get_signer_account(w3, pk)
        contract = get_contract(w3, contract_addr)
        value = amount_wei if token == zero_address() else 0
        tx = contract.functions.deposit(portfolio_id, token, amount_wei).build_transaction({
            "from": acct.address,
            "value": value,
            "gas": 300000,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt["status"] != 1:
            print("Transaction failed", file=sys.stderr)
            return 1
        print("Deposit successful. Tx:", tx_hash.hex())
    except Exception as e:
        print("Error:", e, file=sys.stderr)
