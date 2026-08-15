#!/usr/bin/env python3
"""
WARP Config Generator for AmneziaWG 2.0
Генератор конфигов WARP с автоматической регистрацией
"""

import json
import random
import string
import base64
import secrets
from datetime import datetime
import urllib.request
import urllib.error


class WARPGenerator:
    WARP_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
    
    ENDPOINTS_V4 = [
        "engage.cloudflareclient.com:2408",
        "connect.cloudflareclient.com:2408",
        "wireguard.cloudflareclient.com:2408",
    ]

    ENDPOINTS_V6 = [
        "[2606:4700:d0::a29f:c001]:2408",
        "[2606:4700:d1::a29f:c001]:2408",
        "[2606:4700:d0::a29f:c002]:2408",
        "[2606:4700:d1::a29f:c002]:2408",
    ]

    def __init__(self):
        self.private_key = ""
        self.ipv4_address = ""
        self.ipv6_address = ""

    @staticmethod
    def generate_private_key():
        private_bytes = secrets.token_bytes(32)
        private_array = bytearray(private_bytes)
        private_array[0] &= 248
        private_array[31] &= 127
        private_array[31] |= 64
        return base64.b64encode(bytes(private_array)).decode('utf-8')

    @staticmethod
    def derive_public_key(private_key_b64):
        try:
            from nacl.signing import SigningKey
            private_bytes = base64.b64decode(private_key_b64)
            signing_key = SigningKey(private_bytes)
            public_bytes = bytes(signing_key.verify_key)
            return base64.b64encode(public_bytes).decode('utf-8')
        except ImportError:
            return "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

    def register_device(self):
        print("Генерация ключей...")
        
        self.private_key = self.generate_private_key()
        public_key = self.derive_public_key(self.private_key)
        
        device_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        
        registration_data = {
            "key": public_key,
            "install_id": device_id,
            "fcm_token": "",
            "tos": datetime.now().isoformat() + ".000Z",
            "type": "Android",
            "model": "SM-G998B",
            "locale": "en_US",
            "warp_enabled": True
        }
        
        api_url = "https://api.cloudflareclient.com/v0a2158/reg"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.1",
        }
        
        try:
            json_data = json.dumps(registration_data).encode('utf-8')
            req = urllib.request.Request(api_url, data=json_data, headers=headers, method="POST")
            
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            account = result.get("account", {})
            if "id" in account and "license" in account:
                client_id = result.get("client_id", "")
                if client_id and len(client_id) >= 8:
                    self.ipv4_address = result.get("interface_ipv4", "172.16.0.2") + "/32"
                    v6_prefix = result.get("v6", "")
                    if v6_prefix and ":" in v6_prefix:
                        self.ipv6_address = v6_prefix + "/128"
                    else:
                        rand_hex = ''.join(random.choices('0123456789abcdef', k=4))
                        self.ipv6_address = f"2606:4700:110:{rand_hex}::{device_id[:8]}/128"
                else:
                    rand_ip = random.randint(2, 254)
                    rand_hex = ''.join(random.choices('0123456789abcdef', k=4))
                    self.ipv4_address = f"172.16.0.{rand_ip}/32"
                    self.ipv6_address = f"2606:4700:110:{rand_hex}::1/128"
                
                print("Устройство зарегистрировано в WARP")
                return True
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
        
        rand_ip = random.randint(2, 254)
        rand_hex = ''.join(random.choices('0123456789abcdef', k=4))
        self.ipv4_address = f"172.16.0.{rand_ip}/32"
        self.ipv6_address = f"2606:4700:110:{rand_hex}::1/128"
        return True

    def get_endpoint(self, ipv6=False):
        endpoints = self.ENDPOINTS_V6 if ipv6 else self.ENDPOINTS_V4
        return random.choice(endpoints)

    def generate_config(self, ipv6=True, dns="1.1.1.1"):
        endpoint_v4 = self.get_endpoint(ipv6=False)
        endpoint_v6 = self.get_endpoint(ipv6=True) if ipv6 else None
        
        if ipv6 and endpoint_v6:
            endpoint = f"{endpoint_v4},{endpoint_v6}"
        else:
            endpoint = endpoint_v4
        
        lines = [
            "[Interface]",
            f"PrivateKey = {self.private_key}",
            f"Address = {self.ipv4_address}",
        ]
        
        if ipv6 and self.ipv6_address:
            lines.append(f"Address = {self.ipv6_address}")
        
        lines.extend([
            f"DNS = {dns}",
            "MTU = 1280",
            "SaveConfig = false",
            "Jc = 3",
            "Jmin = 500",
            "Jmax = 1500",
            "S1 = 0",
            "S2 = 0",
            "H1 = 0",
            "H2 = 0",
            "H3 = 0",
            "H4 = 0",
            "",
            "[Peer]",
            f"PublicKey = {self.WARP_PUBLIC_KEY}",
            "AllowedIPs = 0.0.0.0/0, ::/0",
            f"Endpoint = {endpoint}",
            "PersistentKeepalive = 25"
        ])
        
        return "\n".join(lines)

    def save_config(self, config, filename=None):
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"warp_config_{timestamp}.conf"
        
        if not filename.endswith('.conf'):
            filename += '.conf'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(config)
        
        return filename


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     WARP Config Generator for AmneziaWG 2.0              ║
╚══════════════════════════════════════════════════════════╝
""")
    
    generator = WARPGenerator()
    current_config = None
    use_ipv6 = True
    custom_dns = "1.1.1.1"
    
    while True:
        print("""
┌─────────────────────────────────────────┐
│  1. Сгенерировать конфиг                │
│  2. Режим: IPv4+IPv6 / Только IPv4      │
│  3. Настроить DNS                       │
│  4. Сохранить конфиг                    │
│  5. Выход                               │
└─────────────────────────────────────────┘
""")
        
        if current_config:
            print("Конфиг готов")
        
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == '1':
            print("\nРегистрация в WARP и генерация...")
            try:
                if generator.register_device():
                    current_config = generator.generate_config(
                        ipv6=use_ipv6, 
                        dns=custom_dns
                    )
                    print("\nКонфиг сгенерирован!\n")
                    print("=" * 60)
                    print(current_config)
                    print("=" * 60)
            except Exception as e:
                print(f"\nОшибка: {e}")
        
        elif choice == '2':
            mode = "IPv4 + IPv6" if use_ipv6 else "Только IPv4"
            print(f"\nТекущий режим: {mode}")
            toggle = input("Переключить? (y/n): ").strip().lower()
            if toggle == 'y':
                use_ipv6 = not use_ipv6
                mode = "IPv4 + IPv6" if use_ipv6 else "Только IPv4"
                print(f"Режим: {mode}")
        
        elif choice == '3':
            print(f"\nТекущий DNS: {custom_dns}")
            new_dns = input("Новый DNS (Enter для отмены): ").strip()
            if new_dns:
                custom_dns = new_dns
                print(f"DNS: {custom_dns}")
        
        elif choice == '4':
            if not current_config:
                print("\nСначала сгенерируйте конфиг (пункт 1)")
                continue
            
            filename = input("Имя файла (Enter для авто): ").strip()
            try:
                saved_file = generator.save_config(current_config, filename or None)
                print(f"\nСохранено в: {saved_file}")
            except Exception as e:
                print(f"\nОшибка: {e}")
        
        elif choice == '5':
            print("\nПока!")
            break
        
        else:
            print("\nНеверный выбор")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано")
    except Exception as e:
        print(f"\nОшибка: {e}")
