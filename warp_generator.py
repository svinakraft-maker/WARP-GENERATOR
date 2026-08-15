#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WARP Config Generator for AmneziaWG / WireGuard
Generates clean configs without comments, using direct IPs and real API registration.
Zero dependencies (uses system 'wg' or fallback).
"""

import json
import urllib.request
import urllib.error
import socket
import subprocess
import base64
import os

def generate_keys_with_wg():
    """Generate keys using wireguard-tools."""
    try:
        private = subprocess.check_output(['wg', 'genkey'], stderr=subprocess.DEVNULL).decode().strip()
        public = subprocess.check_output(['wg', 'pubkey'], input=private.encode(), stderr=subprocess.DEVNULL).decode().strip()
        return private, public
    except FileNotFoundError:
        return None, None

def generate_keys_with_nacl():
    """Generate keys using pynacl library."""
    try:
        import nacl.signing
        sk = nacl.signing.SigningKey.generate()
        private = base64.b64encode(bytes(sk)).decode('utf-8')
        public = base64.b64encode(bytes(sk.verify_key)).decode('utf-8')
        return private, public
    except ImportError:
        return None, None

def register_warp_device(public_key):
    """Register device with Cloudflare WARP API."""
    api_url = "https://api.cloudflareclient.com/v0a4005/reg"
    
    headers = {
        "User-Agent": "okhttp/3.12.1",
        "Content-Type": "application/json"
    }
    
    payload = {
        "key": public_key,
        "install_id": "",
        "fcm_token": "",
        "tos": "2024-01-01T00:00:00.000Z",
        "type": "Android",
        "model": "SM-G973N",
        "locale": "en_US",
        "warp_enabled": True
    }

    req = urllib.request.Request(
        api_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers, 
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"API Error: {e.code}")
        return None
    except Exception as e:
        print(f"Registration failed: {e}")
        return None

def get_endpoint_ip():
    """Get working WARP endpoint IP."""
    # Try to resolve, fallback to known anycast IPs
    domains = ["engage.cloudflareclient.com", "connect.cloudflareclient.com"]
    fallback_ips = ["162.159.192.1", "162.159.193.1", "188.114.96.1", "188.114.97.1"]
    
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            return f"{ip}:2408"
        except:
            continue
    
    # Fallback to random known IP
    import random
    return f"{random.choice(fallback_ips)}:2408"

def main():
    print("Generating WARP config...")
    
    # Generate keys
    private_key, public_key = generate_keys_with_wg()
    if not private_key:
        private_key, public_key = generate_keys_with_nacl()
    
    if not private_key:
        print("ERROR: Cannot generate keys.")
        print("Install wireguard-tools: sudo apt install wireguard-tools")
        print("OR install pynacl: pip install pynacl")
        return
    
    print(f"Generated keypair: {public_key[:10]}...")
    
    # Register with WARP
    warp_data = register_warp_device(public_key)
    if not warp_data:
        print("Failed to register with WARP API")
        return
    
    account = warp_data.get('account', {})
    config = warp_data.get('config', {})
    
    license_key = account.get('license')
    peer_public_key = config['peers'][0]['public_key']
    
    # Get endpoint
    endpoint = get_endpoint_ip()
    
    # Generate addresses (standard WARP ranges)
    v4_addr = "172.16.0.2/32"
    v6_addr = "2606:4700:110:860e:7394:794:ac4d:31b/128"
    
    # Build clean config
    config_lines = [
        "[Interface]",
        f"Address = {v4_addr}, {v6_addr}",
        f"PrivateKey = {private_key}",
        "DNS = 1.1.1.1, 1.0.0.1",
        "MTU = 1280",
        "",
        "[Peer]",
        f"PublicKey = {peer_public_key}",
        "AllowedIPs = 0.0.0.0/0, ::/0",
        f"Endpoint = {endpoint}",
        "PersistentKeepalive = 25"
    ]
    
    config_text = "\n".join(config_lines)
    
    # Output
    print("\n" + "="*50)
    print("CLEAN CONFIG (No comments):")
    print("="*50)
    print(config_text)
    print("="*50)
    
    # Save
    filename = "warp.conf"
    with open(filename, "w") as f:
        f.write(config_text)
    
    print(f"\nSaved to: {filename}")
    print(f"License Key: {license_key}")

if __name__ == "__main__":
    main()
