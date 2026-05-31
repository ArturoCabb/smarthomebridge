from abc import abstractmethod, ABC

class BaseService(ABC):
    """Base class for all services."""

    @abstractmethod
    def initialize(self):
        """Initialize the service."""
        pass

    def add_accessory(self, device_id: str, accessory):
        """
        Add an accessory to the service.
        """
        pass

    def start(self):
        """Start the service."""
        pass

    def stop(self):
        """Stop the service."""
        pass