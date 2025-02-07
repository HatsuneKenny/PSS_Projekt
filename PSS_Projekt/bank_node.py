#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bankovní P2P Node s dodatečným logováním pro příkaz AC

Tento program implementuje bankovní node podle zadaných kritérií a přidává
detailní logování v metodě create_account() a save() pro diagnostiku problému s příkazem AC.

Popis:
  Podporuje následující příkazy:
    BC – vrací kód banky (IP adresa)
    AC – vytvoří nový bankovní účet (vrací číslo účtu ve formátu "AC <číslo>/<ip>")
    AD – vloží peníze na účet ("AD <číslo>/<ip> <částka>")
    AW – vybere peníze z účtu ("AW <číslo>/<ip> <částka>")
    AB – vrátí zůstatek na účtu ("AB <číslo>/<ip>")
    AR – smaže účet (pokud je zůstatek 0) ("AR <číslo>/<ip>")
    BA – celková částka na všech účtech ("BA <částka>")
    BN – počet klientů (bankovních účtů) ("BN <počet>")
"""

import socket
import socketserver
import threading
import argparse
import logging
import json
import os
import re
import sys

# --- Pomocné funkce ---

def is_valid_ip(ip):
    pattern = r"^\d{1,3}(\.\d{1,3}){3}$"
    if re.match(pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

# --- Třída pro persistentní uložení bankovních dat ---

class BankData:
    def __init__(self, data_file):
        self.data_file = data_file
        # Použijte rekurzivní zámek místo threading.Lock()
        self.lock = threading.RLock()
        self.last_account = 9999  # První účet bude mít číslo 10000
        self.accounts = {}
        self.load()


    def load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_account = data.get("last_account", 9999)
                    self.accounts = data.get("accounts", {})
                logging.info(f"Data načtena ze souboru {self.data_file}: {data}")
            except Exception as e:
                logging.error(f"Chyba při načítání dat: {e}")
                self.last_account = 9999
                self.accounts = {}
        else:
            logging.info(f"Soubor {self.data_file} neexistuje. Inicializuji prázdná data.")
            self.last_account = 9999
            self.accounts = {}

    def save(self):
        with self.lock:
            try:
                data = {"last_account": self.last_account, "accounts": self.accounts}
                logging.info(f"Ukládám data do souboru {self.data_file}: {data}")
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                logging.info("Data úspěšně uložena.")
            except Exception as e:
                logging.error(f"Chyba při ukládání dat: {e}")

    def create_account(self):
        with self.lock:
            logging.info("Vytvářím nový účet...")
            if self.last_account >= 99999:
                logging.error("Maximální počet účtů dosažen.")
                return None, "Naše banka nyní neumožňuje založení nového účtu."
            self.last_account += 1
            account_number = self.last_account
            self.accounts[str(account_number)] = 0
            logging.info(f"Účet {account_number} vytvořen. Volám save()...")
            self.save()
            logging.info(f"Účet {account_number} byl úspěšně vytvořen a data uložena.")
            return account_number, None

    def deposit(self, account_number, amount):
        with self.lock:
            if str(account_number) not in self.accounts:
                return "Bankovní účet neexistuje."
            self.accounts[str(account_number)] += amount
            self.save()
            return None

    def withdraw(self, account_number, amount):
        with self.lock:
            if str(account_number) not in self.accounts:
                return "Bankovní účet neexistuje."
            if self.accounts[str(account_number)] < amount:
                return "Není dostatek finančních prostředků."
            self.accounts[str(account_number)] -= amount
            self.save()
            return None

    def get_balance(self, account_number):
        with self.lock:
            return self.accounts.get(str(account_number), None)

    def remove_account(self, account_number):
        with self.lock:
            if str(account_number) not in self.accounts:
                return "Bankovní účet neexistuje."
            if self.accounts[str(account_number)] != 0:
                return "Nelze smazat bankovní účet na kterém jsou finance."
            del self.accounts[str(account_number)]
            self.save()
            return None

    def total_amount(self):
        with self.lock:
            return sum(self.accounts.values())

    def number_of_clients(self):
        with self.lock:
            return len(self.accounts)

# --- Třída obsluhy klientských spojení ---

class BankRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(self.server.timeout)
        client_ip, client_port = self.client_address
        logging.info(f"Nové spojení od {client_ip}:{client_port}")
        while True:
            try:
                data = self.rfile.readline()
                if not data:
                    break
                command_line = data.decode('utf-8').strip()
                if not command_line:
                    continue
                logging.info(f"Přijat příkaz od {client_ip}:{client_port}: {command_line}")
                response = self.server.process_command(command_line)
                response_line = (response + "\n").encode('utf-8')
                self.wfile.write(response_line)
                self.wfile.flush()
                logging.info(f"Odpověď odeslána {client_ip}:{client_port}: {response}")
            except socket.timeout:
                logging.info(f"Timeout spojení od {client_ip}:{client_port}")
                break
            except Exception as e:
                logging.error(f"Chyba při obsluze klienta {client_ip}:{client_port}: {e}")
                break
        logging.info(f"Ukončení spojení od {client_ip}:{client_port}")

# --- Serverová třída ---

class BankServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, bank_ip, bank_data, timeout):
        super().__init__(server_address, RequestHandlerClass)
        self.bank_ip = bank_ip
        self.bank_data = bank_data
        self.timeout = timeout

    def process_command(self, command_line):
        tokens = command_line.split()
        if not tokens:
            return "ER Prázdný příkaz."
        cmd = tokens[0].upper()

        try:
            if cmd == "BC":
                if len(tokens) != 1:
                    return "ER Příkaz BC má špatný formát."
                return f"BC {self.bank_ip}"

            elif cmd == "AC":
                if len(tokens) != 1:
                    return "ER Příkaz AC má špatný formát."
                account_number, err = self.bank_data.create_account()
                if err:
                    return f"ER {err}"
                return f"AC {account_number}/{self.bank_ip}"

            elif cmd == "AD":
                if len(tokens) != 3:
                    return "ER Příkaz AD má špatný formát."
                account_spec = tokens[1]
                amount_str = tokens[2]
                account_number, ip_part, err = self.parse_account_spec(account_spec)
                if err:
                    return f"ER {err}"
                if ip_part != self.bank_ip:
                    return "ER Banka neodpovídá."
                try:
                    amount = int(amount_str)
                    if amount < 0:
                        raise ValueError
                except:
                    return "ER číslo bankovního účtu a částka není ve správném formátu."
                err = self.bank_data.deposit(account_number, amount)
                if err:
                    return f"ER {err}"
                return "AD"

            elif cmd == "AW":
                if len(tokens) != 3:
                    return "ER Příkaz AW má špatný formát."
                account_spec = tokens[1]
                amount_str = tokens[2]
                account_number, ip_part, err = self.parse_account_spec(account_spec)
                if err:
                    return f"ER {err}"
                if ip_part != self.bank_ip:
                    return "ER Banka neodpovídá."
                try:
                    amount = int(amount_str)
                    if amount < 0:
                        raise ValueError
                except:
                    return "ER číslo bankovního účtu a částka není ve správném formátu."
                err = self.bank_data.withdraw(account_number, amount)
                if err:
                    return f"ER {err}"
                return "AW"

            elif cmd == "AB":
                if len(tokens) != 2:
                    return "ER Příkaz AB má špatný formát."
                account_spec = tokens[1]
                account_number, ip_part, err = self.parse_account_spec(account_spec)
                if err:
                    return f"ER {err}"
                if ip_part != self.bank_ip:
                    return "ER Banka neodpovídá."
                balance = self.bank_data.get_balance(account_number)
                if balance is None:
                    return "ER Bankovní účet neexistuje."
                return f"AB {balance}"

            elif cmd == "AR":
                if len(tokens) != 2:
                    return "ER Příkaz AR má špatný formát."
                account_spec = tokens[1]
                account_number, ip_part, err = self.parse_account_spec(account_spec)
                if err:
                    return f"ER {err}"
                if ip_part != self.bank_ip:
                    return "ER Banka neodpovídá."
                err = self.bank_data.remove_account(account_number)
                if err:
                    return f"ER {err}"
                return "AR"

            elif cmd == "BA":
                if len(tokens) != 1:
                    return "ER Příkaz BA má špatný formát."
                total = self.bank_data.total_amount()
                return f"BA {total}"

            elif cmd == "BN":
                if len(tokens) != 1:
                    return "ER Příkaz BN má špatný formát."
                count = self.bank_data.number_of_clients()
                return f"BN {count}"

            else:
                return "ER Neznámý příkaz."

        except Exception as e:
            logging.exception("Výjimka při zpracování příkazu")
            return "ER Chyba v aplikaci, prosím zkuste to později."

    def parse_account_spec(self, spec):
        parts = spec.split('/')
        if len(parts) != 2:
            return None, None, "Formát čísla účtu není správný."
        account_str, ip = parts
        try:
            account_number = int(account_str)
        except:
            return None, None, "Formát čísla účtu není správný."
        if account_number < 10000 or account_number > 99999:
            return None, None, "Formát čísla účtu není správný."
        if not is_valid_ip(ip):
            return None, None, "Formát IP adresy není správný."
        return account_number, ip, None

# --- Hlavní funkce ---

def main():
    parser = argparse.ArgumentParser(description="Bankovní P2P Node")
    parser.add_argument("--port", type=int, default=65525,
                        help="Port, na kterém server naslouchá (65525-65535)")
    parser.add_argument("--ip", type=str, default=None,
                        help="IP adresa banky (pokud není zadána, získá se automaticky)")
    parser.add_argument("--timeout", type=int, default=5,
                        help="Timeout pro komunikaci s klienty (v sekundách, výchozí 5)")
    parser.add_argument("--datafile", type=str, default="bank_data.json",
                        help="Soubor pro persistentní uložení dat (výchozí bank_data.json)")
    parser.add_argument("--logfile", type=str, default="bank_node.log",
                        help="Soubor pro logování (výchozí bank_node.log)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(args.logfile, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    if args.port < 65525 or args.port > 65535:
        logging.error("Port musí být v rozmezí 65525 až 65535.")
        sys.exit(1)

    if args.ip:
        bank_ip = args.ip
        if not is_valid_ip(bank_ip):
            logging.error("Zadaná IP adresa není validní.")
            sys.exit(1)
    else:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            bank_ip = s.getsockname()[0]
            s.close()
        except Exception as e:
            logging.error(f"Nelze získat lokální IP adresu: {e}")
            bank_ip = "127.0.0.1"

    logging.info(f"Spouštím bankovní node na IP {bank_ip} a portu {args.port}")
    bank_data = BankData(args.datafile)
    server_address = ("", args.port)
    with BankServer(server_address, BankRequestHandler, bank_ip, bank_data, args.timeout) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Ukončuji server (stisknuto Ctrl+C).")

if __name__ == '__main__':
    main()
