#!/usr/bin/env python3
"""
Simple CLI UI for Binance Futures Testnet Bot
"""

from rich.console import Console
from rich.table import Table
from prompt_toolkit import prompt
from basic_bot import BasicBot  # import your existing bot

API_KEY = "        "
API_SECRET = "     "
BASE_URL = "https://testnet.binancefuture.com"

console = Console()
bot = BasicBot(API_KEY, API_SECRET, base_url=BASE_URL)

def show_menu():
    console.print("\n[bold cyan]==============================[/]")
    console.print("[bold yellow]   Binance Futures Test Bot  [/]")
    console.print("[bold cyan]==============================[/]")
    console.print("[green][1][/green] Place Market Order")
    console.print("[green][2][/green] Place Limit Order")
    console.print("[green][3][/green] Query Order Status")
    console.print("[green][4][/green] Cancel Order")
    console.print("[green][5][/green] Check Balance")
    console.print("[green][6][/green] Exit")
    console.print("[bold cyan]==============================[/]\n")

def place_market_order():
    symbol = prompt("Enter symbol (e.g. BTCUSDT): ").upper()
    side = prompt("Side (BUY/SELL): ").upper()
    qty = float(prompt("Quantity: "))
    try:
        resp = bot.place_order(symbol=symbol, side=side, order_type="MARKET", quantity=qty)
        console.print("[bold green]✅ Order placed successfully![/]")
        console.print(resp)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

def place_limit_order():
    symbol = prompt("Enter symbol (e.g. BTCUSDT): ").upper()
    side = prompt("Side (BUY/SELL): ").upper()
    qty = float(prompt("Quantity: "))
    price = float(prompt("Limit price: "))
    try:
        resp = bot.place_order(symbol=symbol, side=side, order_type="LIMIT", quantity=qty, price=price)
        console.print("[bold green]✅ Limit order placed successfully![/]")
        console.print(resp)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

def query_order():
    symbol = prompt("Enter symbol (e.g. BTCUSDT): ").upper()
    order_id = int(prompt("Order ID: "))
    try:
        resp = bot.get_order(symbol=symbol, order_id=order_id)
        console.print("[bold cyan]Order Info:[/]")
        console.print(resp)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

def cancel_order():
    symbol = prompt("Enter symbol (e.g. BTCUSDT): ").upper()
    order_id = int(prompt("Order ID to cancel: "))
    try:
        resp = bot.cancel_order(symbol=symbol, order_id=order_id)
        console.print("[bold green]✅ Order cancelled successfully![/]")
        console.print(resp)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

def check_balance():
    try:
        balances = bot._signed_request("GET", "/fapi/v2/balance")
        table = Table(title="Futures Balance")
        table.add_column("Asset", style="cyan")
        table.add_column("Balance", justify="right", style="green")
        for bal in balances:
            table.add_row(bal["asset"], bal["balance"])
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

def main():
    while True:
        show_menu()
        choice = prompt("Select an option: ").strip()
        if choice == "1":
            place_market_order()
        elif choice == "2":
            place_limit_order()
        elif choice == "3":
            query_order()
        elif choice == "4":
            cancel_order()
        elif choice == "5":
            check_balance()
        elif choice == "6":
            console.print("[bold yellow]Exiting bot... Goodbye![/]")
            break
        else:
            console.print("[red]Invalid choice, try again![/]")

if __name__ == "__main__":
    main()
