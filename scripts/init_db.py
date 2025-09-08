import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine

# Ensure project root is on sys.path so that 'app' package can be imported
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.logger import logger
from app.database.db.session import engine


async def seed_fees(engine: Engine):
    src_dir = CURRENT_FILE.parent / 'src'
    tables = {
        'destination': src_dir / 'destination.csv',
        'location': src_dir / 'location.csv',
        'terminal': src_dir / 'terminal.csv',
        'vehicle_type': src_dir / 'vehicle_type.csv',
        'fee_type': src_dir / 'fee_type.csv',
        'fee': src_dir / 'fee.csv',
        'additional_fee': src_dir / 'additional_fee.csv',
        'additional_special_fee': src_dir / 'additional_special_fee.csv',
        'delivery_price': src_dir / 'prices_delivery.csv',
        'shipping_price': src_dir / 'prices_shipping.csv',
    }

    for table, path in tables.items():
        logger.info(f'Seeding table {table} from {path}')
        df = pd.read_csv(path)
        df.to_sql(table, engine, if_exists='append', index=False)


if __name__ == '__main__':
    import asyncio

    asyncio.run(seed_fees(engine))




