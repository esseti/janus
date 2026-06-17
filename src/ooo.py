#!/usr/bin/env python3
"""CLI to manage the out-of-office period.

Examples:
    uv run python -m src.ooo --start 2026-07-01 --end 2026-07-08
    uv run python -m src.ooo --status
    uv run python -m src.ooo --cancel
    uv run python -m src.ooo --recap
"""

from __future__ import annotations

import sys

from .ooo_state import clear_ooo, is_ooo_active, load_ooo, set_ooo
from .recap import maybe_send_recap


def _print_status() -> None:
    state = load_ooo()
    if not state:
        print("ℹ️  Nessun periodo out-of-office configurato")
        return
    active = "attivo" if is_ooo_active() else "non attivo (oggi fuori dal periodo)"
    flag = "sì" if state.get("active") else "no"
    print("🏖️  Out-of-office:")
    print(f"   • Periodo: {state.get('start')} → {state.get('end')}")
    print(f"   • Flag attivo: {flag} ({active})")
    print(f"   • Recap inviato: {'sì' if state.get('recap_sent') else 'no'}")


def main() -> None:
    """Entry point for `python -m src.ooo`."""
    import argparse

    parser = argparse.ArgumentParser(description="Gestione periodo out-of-office Janus")
    parser.add_argument("--start", help="Data inizio (YYYY-MM-DD, inclusa)")
    parser.add_argument("--end", help="Data fine (YYYY-MM-DD, inclusa)")
    parser.add_argument(
        "--status", action="store_true", help="Mostra lo stato corrente"
    )
    parser.add_argument(
        "--cancel", action="store_true", help="Disattiva l'OOO senza inviare recap"
    )
    parser.add_argument(
        "--recap", action="store_true", help="Forza l'invio del recap adesso"
    )
    args = parser.parse_args()

    if args.status:
        _print_status()
        return

    if args.cancel:
        clear_ooo()
        print("✅ Out-of-office disattivato (nessun recap inviato)")
        return

    if args.recap:
        if not maybe_send_recap(force=True):
            print("ℹ️  Nessun recap da inviare")
        return

    if args.start and args.end:
        try:
            state = set_ooo(args.start, args.end)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(
            f"✅ Out-of-office impostato: {state['start']} → {state['end']}. "
            "Le notifiche saranno trattenute; recap automatico al rientro."
        )
        return

    parser.error("specifica --start e --end, oppure --status / --cancel / --recap")


if __name__ == "__main__":
    main()
