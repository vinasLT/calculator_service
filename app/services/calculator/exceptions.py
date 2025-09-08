class LocationNotFoundError(Exception):
    def __init__(self, message="Location not found"):
        self.message = message
        super().__init__(self.message)

class DestinationNotFoundError(Exception):
    def __init__(self, message="Destination not found"):
        self.message = message
        super().__init__(self.message)

