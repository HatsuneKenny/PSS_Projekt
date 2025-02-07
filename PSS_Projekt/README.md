# Bank P2P Node

Bank P2P Node je Pythonová aplikace, která simuluje bankovní systém v peer-to-peer síti. Program umožňuje vytvářet bankovní účty, vkládat a vybírat peníze, získávat zůstatky, mazat účty (pokud mají nulový zůstatek) a získávat statistiky o celkové sumě prostředků či počtu klientů. Komunikace probíhá pomocí TCP/IP na konfigurovatelném portu a data jsou persistentně uložena do JSON souboru.

## Obsah

- [Přehled](#přehled)
- [Funkce](#funkce)
- [Požadavky](#požadavky)
- [Instalace](#instalace)
- [Použití](#použití)
  - [Syntaxe příkazů](#syntaxe-příkazů)
- [Konfigurace](#konfigurace)
- [Testování](#testování)
- [Struktura kódu](#struktura-kódu)
- [Licence](#licence)

## Přehled

Tento projekt implementuje bankovní node s následujícími příkazy:

- **BC** – vrací kód banky (IP adresu).
- **AC** – založí nový bankovní účet a vrátí číslo účtu ve formátu `AC <číslo>/<ip>`.
- **AD** – vloží peníze na účet, formát: `AD <číslo>/<ip> <částka>`.
- **AW** – vybere peníze z účtu, formát: `AW <číslo>/<ip> <částka>`.
- **AB** – dotazuje zůstatek na účtu, formát: `AB <číslo>/<ip>`.
- **AR** – smaže účet (pouze pokud je zůstatek 0), formát: `AR <číslo>/<ip>`.
- **BA** – vrací celkovou částku všech účtů, formát: `BA`.
- **BN** – vrací počet aktivních bankovních účtů, formát: `BN`.

## Funkce

- **Persistentní úložiště:** Údaje o účtech se ukládají do JSON souboru (výchozí `bank_data.json`), takže po restartu aplikace nedochází ke ztrátě dat.
- **Paralelní obsluha klientů:** Server využívá multithreading (ThreadingTCPServer) pro obsluhu více klientských spojení.
- **Konfigurovatelnost:** Parametry jako port, IP adresa, timeout, název souboru s daty a logovací soubor lze snadno nastavit pomocí argumentů příkazové řádky.
- **Logování:** Aplikace loguje události do konzole i do logovacího souboru (výchozí `bank_node.log`).

## Požadavky

- Python 3.x
- Standardní knihovny: `socket`, `socketserver`, `threading`, `argparse`, `logging`, `json`, `os`, `re`, `sys`

## Instalace

1. Ujistěte se, že máte nainstalovaný Python 3.
2. Stáhněte si zdrojový kód projektu (například soubor `bank_node.py`).
3. Otevřete terminál a přejděte do adresáře, kde se soubor nachází.

## Zdroje

1. Školní cvičení
2. Geeks4Geeks: https://www.geeksforgeeks.org/what-is-p2p-peer-to-peer-process/

## Použití
Putty:
-Otevřete Putty a do IP zadejte vaší IP, do portu 65525 a connection type RAW!
-Poté spusťte

Python:
Spusťte server následovně:

```bash
cd C:\cesta\k\vašemu\projektu
python3 bank_node.py --port 65525 --timeout 5
