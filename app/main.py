import argparse
import asyncio
import sys

from app.database import setup_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cita Previa Bot")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--discover", action="store_true", help="Run interactive discovery mode")
    group.add_argument("--telegram-test", action="store_true", help="Send a Telegram test message")
    group.add_argument("--check", action="store_true", help="Run one availability check and exit")
    group.add_argument("--monitor", action="store_true", help="Poll for availability on a loop")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    setup_database()

    if args.discover:
        from app.discovery import run_discovery
        await run_discovery()

    elif args.telegram_test:
        from app.telegram_bot import telegram_test
        await telegram_test()

    elif args.check:
        from app.checker import check_once, _record
        result = await check_once()
        _record(result)
        print(f"[check] status={result['status']}  slots_available={result['slots_available']}")

    elif args.monitor:
        from app.checker import run_checker
        from app.config import CHECK_INTERVAL_SECONDS
        await run_checker(CHECK_INTERVAL_SECONDS)


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n[main] Interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
