import asyncio
from datetime import datetime, UTC
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.additional_fee import AdditionalFeeService
from app.database.crud.additional_special_fee import AdditionalSpecialFeeService
from app.database.crud.delivery_price import DeliveryPriceService
from app.database.crud.destination import DestinationService
from app.database.crud.exchange_rate import ExchangeRateService
from app.database.crud.fee import FeeService
from app.database.crud.fee_type import FeeTypeService
from app.database.crud.location import LocationService
from app.database.crud.shipping_price import ShippingPriceService
from app.database.crud.vehicle_type import VehicleTypeService
from app.database.db.session import AsyncSessionLocal
from app.database.models import DeliveryPrice
from currency_converter import CurrencyConverter
from app.enums.auction import AuctionEnum
from app.enums.fee_type import FeeTypeEnum
from app.enums.vehicle_type import VehicleTypeEnum
from app.schemas.calculator import CalculatorDataIn
from app.services.calculator.types import City, DefaultCalculator, AdditionalFeesOut, EUCalculator, VATs, CalculatorOut


class CalculatorService:
    BROKER_FEE = 250

    # add other additional fees for biaduto


    def __init__(self,
                 db: AsyncSession,
                 price: int,
                 auction: AuctionEnum,
                 fee_type: FeeTypeEnum,
                 location: str,
                 vehicle_type: VehicleTypeEnum,
                 vehicle_location: str | None = None,
                 destination: str | None = None):
        self.data = CalculatorDataIn(price=price,
                                     auction=auction,
                                     fee_type=fee_type,
                                     location=location,
                                     vehicle_type=vehicle_type,
                                     destination=destination,
                                     vehicle_location=vehicle_location)
        self.db = db

    async def additional_fees_calculator(self) -> AdditionalFeesOut:
        additional_special_fee_service = AdditionalSpecialFeeService(self.db)
        fee_type_service = FeeTypeService(self.db)
        fee_service = FeeService(self.db)
        additional_fee_service = AdditionalFeeService(self.db)


        fees = await additional_special_fee_service.get_additional_special_fee(self.data.auction)

        all_fees_summ = sum([fee.amount for fee in fees])


        if self.data.fee_type:
            fee_type = await fee_type_service.get_by_fee_auction(self.data.auction, self.data.fee_type)
        else:
            fee_type = await fee_type_service.get_by_fee_auction(self.data.auction, FeeTypeEnum.NON_CLEAN_TITLE_FEE)
            all_fee_types = await fee_type_service.get_all()
            print(all_fee_types)



        internet_fee = 0
        live_fee = 0


        auction_fee_obj = await fee_service.get_fee_in_car_price(fee_type, self.data.price)


        if auction_fee_obj.car_price_fee < 1:
            auction_fee = self.data.price * auction_fee_obj.car_price_fee
        else:
            auction_fee = auction_fee_obj.car_price_fee

        if self.data.auction == AuctionEnum.IAAI:
            internet_fee = await additional_fee_service.get_price_in_int_proxy(self.data.price)
            internet_fee = internet_fee.int_fee
        elif self.data.auction == AuctionEnum.COPART:
            live_fee = await additional_fee_service.get_price_in_live(self.data.price)
            live_fee = live_fee.live_bid_fee

        addit_fees = all_fees_summ + int(auction_fee) + internet_fee + live_fee

        # invoice_fees = {
        #     'auction_fee': auction_fee,
        #     'internet_fee': internet_fee,
        #     'live_fee': live_fee
        # }
        return AdditionalFeesOut(summ=addit_fees, auction_fee=auction_fee, live_fee=live_fee, internet_fee=int(internet_fee))

    @staticmethod
    def sync_terminals( delivery_cities: list[City], shipping_terminals: list[City]):
        delivery_names = {city.name for city in delivery_cities}
        shipping_names = {terminal.name for terminal in shipping_terminals}

        common_names = delivery_names & shipping_names

        filtered_delivery = [city for city in delivery_cities if city.name in common_names]
        filtered_shipping = [terminal for terminal in shipping_terminals if terminal.name in common_names]

        return filtered_delivery, filtered_shipping

    async def calculate(self):
        vehicle_type_service = VehicleTypeService(self.db)
        location_service = LocationService(self.db)
        destination_service = DestinationService(self.db)
        shipping_price_service = ShippingPriceService(self.db)
        delivery_price_service = DeliveryPriceService(self.db)
        exchange_rate_service = ExchangeRateService(self.db)

        vehicle_type_obj = await vehicle_type_service.get_by_auction_and_type(
            auction=self.data.auction,
            vehicle_type=self.data.vehicle_type
        )

        if self.data.destination is None:
            destination = await destination_service.get_default()
        else:
            destination = await destination_service.get_by_name(name=self.data.destination)

        additional_fees = await self.additional_fees_calculator()

        delivery_location_obj = await location_service.get_location(self.data.location, vehicle_type_obj)
        print(delivery_location_obj.name)
        if not delivery_location_obj:
            return None

        delivery_prices = await delivery_price_service.get_by_terminal_location_vehicle_type(
            location=delivery_location_obj,
            vehicle_type=vehicle_type_obj
        )
        shipping_prices = await shipping_price_service.get_by_destination_and_vehicle_type(destination,
                                                                                           vehicle_type_obj)

        delivery_cities = [City(name=delivery_price.terminal.name, price=delivery_price.price) for delivery_price in
                           delivery_prices]
        shipping_terminals = [City(name=shipping_price.terminal.name, price=shipping_price.price) for shipping_price in
                              shipping_prices]

        delivery_cities, shipping_terminals = self.sync_terminals(delivery_cities, shipping_terminals)

        rate = await exchange_rate_service.get_last_rate()
        rate = rate.rate

        custom_agency = round(350 / rate, 1)

        # Обычный калькулятор (в долларах)
        total_default: list[City] = []
        for delivery, shipping in zip(delivery_cities, shipping_terminals):
            total_price = (
                    delivery.price +
                    shipping.price +
                    additional_fees.summ +
                    self.BROKER_FEE +
                    self.data.price
            )
            total_default.append(City(name=delivery.name, price=round(total_price)))

        calculator = DefaultCalculator(
            broker_fee=self.BROKER_FEE,
            transportation_price=delivery_cities,
            ocean_ship=shipping_terminals,
            additional=additional_fees.summ,
            auction_fee=additional_fees.auction_fee,
            live_fee=additional_fees.live_fee,
            internet_fee=additional_fees.internet_fee,
            totals=total_default
        )

        # ЕС калькулятор (в долларах)
        eu_vats_list: list[City] = []
        vats_list: list[City] = []
        total_eu: list[City] = []

        for delivery, shipping in zip(delivery_cities, shipping_terminals):
            base_sum = (
                    self.BROKER_FEE +
                    shipping.price +
                    delivery.price +
                    additional_fees.summ +
                    self.data.price
            )

            eu_vat = round(base_sum * 0.1)
            eu_vats_list.append(City(name=delivery.name, price=eu_vat))

            vat = round((eu_vat + base_sum) * 0.21)
            vats_list.append(City(name=delivery.name, price=vat))

            total_price_eu = round(
                delivery.price +
                self.BROKER_FEE +
                additional_fees.summ +
                self.data.price +
                eu_vat +
                vat +
                shipping.price +
                custom_agency
            )
            total_eu.append(City(name=delivery.name, price=total_price_eu))

        vats_obj = VATs(
            eu_vats=eu_vats_list,
            vats=vats_list
        )

        eu_calculator = EUCalculator(
            broker_fee=self.BROKER_FEE,
            transportation_price=delivery_cities,
            ocean_ship=shipping_terminals,
            additional=additional_fees.summ,
            vats=vats_obj,
            custom_agency=int(custom_agency),
            totals=total_eu
        )

        # Пересчет в евро
        delivery_cities_euro = [City(name=city.name, price=round(city.price / rate)) for city in delivery_cities]
        shipping_terminals_euro = [City(name=terminal.name, price=round(terminal.price / rate)) for terminal in
                                   shipping_terminals]

        broker_fee_euro = round(self.BROKER_FEE / rate, 1)
        additional_fees_euro = round(additional_fees.summ / rate, 1)
        auction_fee_euro = round(additional_fees.auction_fee / rate, 1)
        live_fee_euro = round(additional_fees.live_fee / rate, 1)
        internet_fee_euro = round(additional_fees.internet_fee / rate, 1)
        price_euro = round(self.data.price / rate, 1)

        # Обычный калькулятор в евро
        total_default_euro: list[City] = []
        for delivery_euro, shipping_euro in zip(delivery_cities_euro, shipping_terminals_euro):
            total_price_euro = (
                    delivery_euro.price +
                    shipping_euro.price +
                    additional_fees_euro +
                    broker_fee_euro +
                    price_euro
            )
            total_default_euro.append(City(name=delivery_euro.name, price=round(total_price_euro)))

        calculator_in_euro = DefaultCalculator(
            broker_fee=round(broker_fee_euro),
            transportation_price=delivery_cities_euro,
            ocean_ship=shipping_terminals_euro,
            additional=round(additional_fees_euro),
            auction_fee=round(auction_fee_euro),
            live_fee=round(live_fee_euro),
            internet_fee=round(internet_fee_euro),
            totals=total_default_euro
        )

        # ЕС калькулятор в евро
        eu_vats_list_euro: list[City] = []
        vats_list_euro: list[City] = []
        total_eu_euro: list[City] = []

        for delivery_euro, shipping_euro in zip(delivery_cities_euro, shipping_terminals_euro):
            base_sum_euro = (
                    broker_fee_euro +
                    shipping_euro.price +
                    delivery_euro.price +
                    additional_fees_euro +
                    price_euro
            )

            eu_vat_euro = round(base_sum_euro * 0.1, 1)
            eu_vats_list_euro.append(City(name=delivery_euro.name, price=round(eu_vat_euro)))

            vat_euro = round((eu_vat_euro + base_sum_euro) * 0.21, 1)
            vats_list_euro.append(City(name=delivery_euro.name, price=round(vat_euro)))

            total_price_eu_euro = round(
                delivery_euro.price +
                broker_fee_euro +
                additional_fees_euro +
                price_euro +
                eu_vat_euro +
                vat_euro +
                shipping_euro.price +
                350  # custom_agency уже в евро
                , 1)
            total_eu_euro.append(City(name=delivery_euro.name, price=round(total_price_eu_euro)))

        vats_obj_euro = VATs(
            eu_vats=eu_vats_list_euro,
            vats=vats_list_euro
        )

        eu_calculator_in_euro = EUCalculator(
            broker_fee=round(broker_fee_euro),
            transportation_price=delivery_cities_euro,
            ocean_ship=shipping_terminals_euro,
            additional=round(additional_fees_euro),
            vats=vats_obj_euro,
            custom_agency=350,  # custom_agency уже в евро
            totals=total_eu_euro
        )

        return CalculatorOut(
            calculator=calculator,
            eu_calculator=eu_calculator,
            calculator_in_euro=calculator_in_euro,
            eu_calculator_in_euro=eu_calculator_in_euro
        )


if __name__ == "__main__":
    async def main():
        db = AsyncSessionLocal()
        time_start = datetime.now(UTC)
        calculator = CalculatorService(db, 1000, AuctionEnum.COPART, None, "TX - Dallas", VehicleTypeEnum.CAR)
        data = await calculator.calculate()
        calc = data.calculator
        eu_calc = data.eu_calculator
        calc_euro = data.calculator_in_euro
        eu_calc_euro = data.eu_calculator_in_euro

        def format_city_list(cities, title="", currency="$"):
            """Форматирует список городов с ценами"""
            if not cities:
                return f"  {title}: Нет данных"

            result = f"  {title}:\n" if title else ""
            for city in cities:
                if currency == "€":
                    result += f"    • {city.name}: {city.price:,.1f} €\n"
                else:
                    result += f"    • {city.name}: {city.price:,} $\n"
            return result.rstrip()

        def format_price(price, label="", currency="$"):
            """Форматирует цену с разделителями тысяч"""
            if currency == "€":
                return f"  {label}: {price:,.1f} €"
            else:
                return f"  {label}: {price:,} $"

        print("=" * 80)
        print("🧮 КАЛЬКУЛЯТОР РАСЧЕТОВ")
        print("=" * 80)

        # Основной калькулятор (USD)
        print("\n📊 ОСНОВНОЙ КАЛЬКУЛЯТОР (USD)")
        print("-" * 50)
        print(format_price(calc.broker_fee, "Комиссия брокера"))
        print(format_price(calc.auction_fee, "Аукционный сбор"))
        print(format_price(calc.live_fee, "Live аукцион"))
        print(format_price(calc.internet_fee, "Интернет аукцион"))
        print(format_price(calc.additional, "Дополнительные расходы"))

        print(f"\n🚚 Стоимость доставки по городам:")
        print(format_city_list(calc.transportation_price))

        print(f"\n🚢 Морская доставка:")
        print(format_city_list(calc.ocean_ship))

        print(f"\n💰 Итоговые суммы по городам:")
        print(format_city_list(calc.totals))

        # EU калькулятор (USD)
        print("\n" + "=" * 80)
        print("🇪🇺 ЕВРОПЕЙСКИЙ КАЛЬКУЛЯТОР (USD)")
        print("-" * 50)
        print(format_price(eu_calc.broker_fee, "Комиссия брокера"))
        print(format_price(eu_calc.custom_agency, "Таможенное агентство"))
        print(format_price(eu_calc.additional, "Дополнительные расходы"))

        print(f"\n🚚 Стоимость доставки по городам:")
        print(format_city_list(eu_calc.transportation_price))

        print(f"\n🚢 Морская доставка:")
        print(format_city_list(eu_calc.ocean_ship))

        print(f"\n📋 НДС:")
        print(format_city_list(eu_calc.vats.vats, "Обычный НДС"))
        print(format_city_list(eu_calc.vats.eu_vats, "Европейский НДС"))

        print(f"\n💰 Итоговые суммы по городам:")
        print(format_city_list(eu_calc.totals))

        # Основной калькулятор (EUR)
        print("\n" + "=" * 80)
        print("📊 ОСНОВНОЙ КАЛЬКУЛЯТОР (EUR)")
        print("-" * 50)
        print(format_price(calc_euro.broker_fee, "Комиссия брокера", "€"))
        print(format_price(calc_euro.auction_fee, "Аукционный сбор", "€"))
        print(format_price(calc_euro.live_fee, "Live аукцион", "€"))
        print(format_price(calc_euro.internet_fee, "Интернет аукцион", "€"))
        print(format_price(calc_euro.additional, "Дополнительные расходы", "€"))

        print(f"\n🚚 Стоимость доставки по городам:")
        print(format_city_list(calc_euro.transportation_price, currency="€"))

        print(f"\n🚢 Морская доставка:")
        print(format_city_list(calc_euro.ocean_ship, currency="€"))

        print(f"\n💰 Итоговые суммы по городам:")
        print(format_city_list(calc_euro.totals, currency="€"))

        # EU калькулятор (EUR)
        print("\n" + "=" * 80)
        print("🇪🇺 ЕВРОПЕЙСКИЙ КАЛЬКУЛЯТОР (EUR)")
        print("-" * 50)
        print(format_price(eu_calc_euro.broker_fee, "Комиссия брокера", "€"))
        print(format_price(eu_calc_euro.custom_agency, "Таможенное агентство", "€"))
        print(format_price(eu_calc_euro.additional, "Дополнительные расходы", "€"))

        print(f"\n🚚 Стоимость доставки по городам:")
        print(format_city_list(eu_calc_euro.transportation_price, currency="€"))

        print(f"\n🚢 Морская доставка:")
        print(format_city_list(eu_calc_euro.ocean_ship, currency="€"))

        print(f"\n📋 НДС:")
        print(format_city_list(eu_calc_euro.vats.vats, "Обычный НДС", "€"))
        print(format_city_list(eu_calc_euro.vats.eu_vats, "Европейский НДС", "€"))

        print(f"\n💰 Итоговые суммы по городам:")
        print(format_city_list(eu_calc_euro.totals, currency="€"))

        print("\n" + "=" * 80)

        # Краткая сводка
        total_basic_usd = sum(city.price for city in calc.totals) if calc.totals else 0
        total_eu_usd = sum(city.price for city in eu_calc.totals) if eu_calc.totals else 0
        total_basic_eur = sum(city.price for city in calc_euro.totals) if calc_euro.totals else 0
        total_eu_eur = sum(city.price for city in eu_calc_euro.totals) if eu_calc_euro.totals else 0

        print("📈 КРАТКАЯ СВОДКА")
        print("-" * 50)
        print("💵 В долларах:")
        print(f"  Общая сумма (основной): {total_basic_usd:,} $")
        print(f"  Общая сумма (EU): {total_eu_usd:,} $")
        print(f"  Разница: {abs(total_eu_usd - total_basic_usd):,} $")

        print("\n💶 В евро:")
        print(f"  Общая сумма (основной): {total_basic_eur:,.1f} €")
        print(f"  Общая сумма (EU): {total_eu_eur:,.1f} €")
        print(f"  Разница: {abs(total_eu_eur - total_basic_eur):,.1f} €")

        print("\n🔄 Сравнение валют:")
        print(f"  Основной USD vs EUR: {total_basic_usd:,} $ ≈ {total_basic_eur:,.1f} €")
        print(f"  EU USD vs EUR: {total_eu_usd:,} $ ≈ {total_eu_eur:,.1f} €")

        print("=" * 80)

        time_done = datetime.now(UTC)
        print(f"Time: {time_done - time_start} seconds")
        await db.close()


    asyncio.run(main())






















