class LocationNotFoundError(Exception):
    def __init__(self, message="Location not found"):
        self.message = message
        super().__init__(self.message)

class DestinationNotFoundError(Exception):
    def __init__(self, message="Destination not found"):
        self.message = message
        super().__init__(self.message)


class VehicleTypeNotFoundError(Exception):
    def __init__(self, message="Vehicle type not found"):
        self.message = message
        super().__init__(self.message)

class ShippingPriceNotFoundError(Exception):
    def __init__(self, message="Shipping price not found"):
        self.message = message
        super().__init__(self.message)

class DeliveryPriceNotFoundError(Exception):
    def __init__(self, message="Delivery price not found"):
        self.message = message
        super().__init__(self.message)


