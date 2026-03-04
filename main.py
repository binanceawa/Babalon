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
