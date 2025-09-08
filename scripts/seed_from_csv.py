import pandas as pd
from sqlalchemy import Engine
from app.core.logger import logger
from app.database.db.session import  engine


async def seed_fees(engine: Engine):
    tabels = {
        'destination': 'src/destination.csv',
        'location': 'src/location.csv',
        'terminal': 'src/terminal.csv',
        'vehicle_type': 'src/vehicle_type.csv',
        'fee_type': 'src/fee_type.csv',
        'fee': 'src/fee.csv',
        'additional_fee': 'src/additional_fee.csv',
        'additional_special_fee': 'src/additional_special_fee.csv',
        'delivery_price': 'src/prices_delivery.csv',
        'shipping_price': 'src/prices_shipping.csv',
    }

    for table, path in tabels.items():
        logger.info(f'Seeding table {table} from {path}')
        df = pd.read_csv(path)
        df.to_sql(table, engine, if_exists='replace', index=False)



if __name__ == '__main__':
    import asyncio
    asyncio.run(seed_fees(engine))




