import logging
from typing import Any, Callable, Dict

from src.services.service_groq import GroqService
from src.services.service_mistral import MistralService  # Assuming this exists

logger = logging.getLogger(__name__)

# Mapping of service names to their respective LLM service classes
SERVICE_FACTORIES: Dict[str, Callable] = {
    "groq": GroqService,
    "mistral": MistralService,  # Example for Mistral service
    # Add more services as they become available
}


def get_service_for_name(service_name: str, config: dict) -> Any:
    """
    Returns the appropriate service instance based on the service name.
    """
    try:
        if service_name not in SERVICE_FACTORIES:
            raise ValueError(f"Unsupported service: {service_name}")

        # Instantiate the service and return it
        service_class = SERVICE_FACTORIES[service_name]
        return service_class(config)  # Assuming config is passed to each service
    except Exception as e:
        logger.error(f"[dispatcher] Error getting service for {service_name}: {e}")
        raise
