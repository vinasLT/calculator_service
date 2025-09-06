import pandas as pd
import math

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logger import logger
from app.database.crud.delivery_price import DeliveryPriceService
from app.database.crud.destination import DestinationService
from app.database.crud.fee import FeeService
from app.database.crud.fee_type import FeeTypeService
from app.database.crud.location import LocationService
from app.database.crud.shipping_price import ShippingPriceService
from app.database.crud.terminal import TerminalService
from app.database.crud.vehicle_type import VehicleTypeService
from app.database.db.session import AsyncSessionLocal, engine_async, engine
from app.database.schemas.destination import DestinationCreate
from app.database.schemas.location import LocationCreate
from app.database.schemas.terminal import TerminalCreate
from app.database.schemas.vehicle_type import VehicleTypeCreate
from app.enums.auction import AuctionEnum
from app.enums.vehicle_type import VehicleTypeEnum




def _to_int_or_none(value):
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
        # pandas may provide numpy types; use float check for NaN
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)
    except Exception:
        return None


async def seed_from_csv():
    df = pd.read_csv('src/prices_delivery.csv')

    # Use async context manager so connections are returned reliably.
    async with AsyncSessionLocal() as db:

        terminal_service = TerminalService(db)
        location_service = LocationService(db)
        vehicle_type_service = VehicleTypeService(db)
        delivery_price_service = DeliveryPriceService(db)

        # Vehicle types: get or create
        iaai_car = await vehicle_type_service.get_by_auction_and_type(AuctionEnum.IAAI, VehicleTypeEnum.CAR)
        if iaai_car is None:
            iaai_car = await vehicle_type_service.create(
                VehicleTypeCreate(auction=AuctionEnum.IAAI, vehicle_type=VehicleTypeEnum.CAR)
            )

        iaai_moto = await vehicle_type_service.get_by_auction_and_type(AuctionEnum.IAAI, VehicleTypeEnum.MOTO)
        if iaai_moto is None:
            iaai_moto = await vehicle_type_service.create(
                VehicleTypeCreate(auction=AuctionEnum.IAAI, vehicle_type=VehicleTypeEnum.MOTO)
            )

        copart_car = await vehicle_type_service.get_by_auction_and_type(AuctionEnum.COPART, VehicleTypeEnum.CAR)
        if copart_car is None:
            copart_car = await vehicle_type_service.create(
                VehicleTypeCreate(auction=AuctionEnum.COPART, vehicle_type=VehicleTypeEnum.CAR)
            )

        copart_moto = await vehicle_type_service.get_by_auction_and_type(AuctionEnum.COPART, VehicleTypeEnum.MOTO)
        if copart_moto is None:
            copart_moto = await vehicle_type_service.create(
                VehicleTypeCreate(auction=AuctionEnum.COPART, vehicle_type=VehicleTypeEnum.MOTO)
            )

        all_terminals = df['Yard'].dropna().unique()
        print(all_terminals)

        # Terminals: get or create
        for terminal_name in all_terminals:
            existing_terminal = await terminal_service.get_by_name(terminal_name)
            if existing_terminal is None:
                await terminal_service.create(TerminalCreate(name=terminal_name))

        all_locations = df['Branch'].dropna().unique()

        for location_name in all_locations:
            auction_row = df[df['Branch'] == location_name].iloc[0]
            auction = auction_row.get('Auction')
            terminal_name = auction_row.get('Yard')
            car_price_raw = auction_row.get('Car fee')
            moto_price_raw = auction_row.get('Motorcycle fee')

            car_price = _to_int_or_none(car_price_raw)
            moto_price = _to_int_or_none(moto_price_raw)

            state = location_name.split(' - ')[0].strip() if ' - ' in location_name else ''
            city = location_name.split(' - ')[1].strip() if ' - ' in location_name else ''

            # Resolve Terminal model instance once (needed for both branches)
            terminal_obj = await terminal_service.get_by_name(terminal_name)
            if terminal_obj is None:
                logger.warning("Terminal '%s' not found for location '%s'; skipping", terminal_name, location_name)
                continue

            # Location: get or create
            location_obj = await location_service.get_by_name(location_name)
            if location_obj is None:
                location_obj = await location_service.create(LocationCreate(
                    name=location_name,
                    state=state,
                    city=city,
                ))

            # Delivery prices: create only if not exists and price present
            if auction == 'IAA':
                if car_price is not None:
                    existing = await delivery_price_service.get_by_terminal_location_vehicle_type(
                        terminal=terminal_obj, location=location_obj, vehicle_type=iaai_car
                    )
                    if not existing:
                        await delivery_price_service.create_with_terminal_location_vehicle_type(
                            price=car_price, terminal=terminal_obj, location=location_obj, vehicle_type=iaai_car
                        )

                if moto_price is not None:
                    existing = await delivery_price_service.get_by_terminal_location_vehicle_type(
                        terminal=terminal_obj, location=location_obj, vehicle_type=iaai_moto
                    )
                    if not existing:
                        await delivery_price_service.create_with_terminal_location_vehicle_type(
                            price=moto_price, terminal=terminal_obj, location=location_obj, vehicle_type=iaai_moto
                        )
            else:
                if car_price is not None:
                    existing = await delivery_price_service.get_by_terminal_location_vehicle_type(
                        terminal=terminal_obj, location=location_obj, vehicle_type=copart_car
                    )
                    if not existing:
                        await delivery_price_service.create_with_terminal_location_vehicle_type(
                            price=car_price, terminal=terminal_obj, location=location_obj, vehicle_type=copart_car
                        )

                if moto_price is not None:
                    existing = await delivery_price_service.get_by_terminal_location_vehicle_type(
                        terminal=terminal_obj, location=location_obj, vehicle_type=copart_moto
                    )
                    if not existing:
                        await delivery_price_service.create_with_terminal_location_vehicle_type(
                            price=moto_price, terminal=terminal_obj, location=location_obj, vehicle_type=copart_moto
                        )

        # seed shipping prices
        df = pd.read_csv('src/prices_shipping.csv')

        all_destinations = df['destination'].dropna().unique()
        all_terminals = df['terminal'].dropna().unique()
        print(all_terminals)
        destination_service = DestinationService(db)
        shipping_price_service = ShippingPriceService(db)

        # Terminals (shipping): get or create
        for terminal_name in all_terminals:
            existing_terminal = await terminal_service.get_by_name(terminal_name)
            if existing_terminal is None:
                await terminal_service.create(TerminalCreate(name=terminal_name))

        # Destinations: get or create
        for destination_name in all_destinations:
            existing_dest = await destination_service.get_by_name(destination_name)
            if existing_dest is None:
                await destination_service.create(DestinationCreate(name=destination_name))

        for row in df.itertuples(index=False):
            terminal_name = getattr(row, 'terminal', None)
            print(terminal_name)
            destination_name = getattr(row, 'destination', None)
            car_price_raw = getattr(row, 'car_price', None)
            moto_price_raw = getattr(row, 'moto_price', None)

            if terminal_name is None or destination_name is None:
                logger.warning("Skipping row with missing terminal/destination: %s", row)
                continue

            terminal_obj = await terminal_service.get_by_name(terminal_name)
            if terminal_obj is None:
                logger.warning("Terminal '%s' not found; skipping shipping price row", terminal_name)
                continue

            # We created destinations above; fetch the model instance to pass into ORM.
            destination_obj = await destination_service.get_by_name(destination_name)
            if destination_obj is None:
                logger.warning("Destination '%s' not found; skipping shipping price row", destination_name)
                continue

            car_price = _to_int_or_none(car_price_raw)
            moto_price = _to_int_or_none(moto_price_raw)

            # Create shipping prices only if not exists and price present
            if car_price is not None:
                existing = await shipping_price_service.get_by_destination_vehicle_type_terminal_single(
                    destination=destination_obj, terminal=terminal_obj, vehicle_type=iaai_car
                )
                if existing is None:
                    await shipping_price_service.create_by_destination_vehicle_type_terminal(
                        price=car_price, destination=destination_obj, terminal=terminal_obj, vehicle_type=iaai_car
                    )
            if moto_price is not None:
                existing = await shipping_price_service.get_by_destination_vehicle_type_terminal_single(
                    destination=destination_obj, terminal=terminal_obj, vehicle_type=iaai_moto
                )
                if existing is None:
                    await shipping_price_service.create_by_destination_vehicle_type_terminal(
                        price=moto_price, destination=destination_obj, terminal=terminal_obj, vehicle_type=iaai_moto
                    )
            if car_price is not None:
                existing = await shipping_price_service.get_by_destination_vehicle_type_terminal_single(
                    destination=destination_obj, terminal=terminal_obj, vehicle_type=copart_car
                )
                if existing is None:
                    await shipping_price_service.create_by_destination_vehicle_type_terminal(
                        price=car_price, destination=destination_obj, terminal=terminal_obj, vehicle_type=copart_car
                    )
            if moto_price is not None:
                existing = await shipping_price_service.get_by_destination_vehicle_type_terminal_single(
                    destination=destination_obj, terminal=terminal_obj, vehicle_type=copart_moto
                )
                if existing is None:
                    await shipping_price_service.create_by_destination_vehicle_type_terminal(
                        price=moto_price, destination=destination_obj, terminal=terminal_obj, vehicle_type=copart_moto
                    )


async def seed_fees(engine: Engine):
    df = pd.read_csv('src/calculator_feetype.csv')
    df.to_sql('fee_type', engine, if_exists='replace', index=False)
    df = pd.read_csv('src/calculator_fee.csv')
    df.to_sql('fee', engine, if_exists='replace', index=False)

    df = pd.read_csv('src/calculator_additionalfees.csv')
    df.to_sql('additional_fee', engine, if_exists='replace', index=False)

    df = pd.read_csv('src/additional_special_fee.csv')
    df.to_sql('additional_special_fee', engine, if_exists='replace', index=False)







if __name__ == '__main__':
    import asyncio
    asyncio.run(seed_from_csv())

    asyncio.run(seed_fees(engine))




