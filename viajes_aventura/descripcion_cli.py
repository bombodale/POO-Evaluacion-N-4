from .models import Destination
from .services import TravelService


def show_destinations(service: TravelService) -> None:
    destinations = service.list_destinations()
    if not destinations:
        print("Todavia no hay destinos registrados.")
        return
    for destination in destinations:
        _print_destination(destination)


def _print_destination(destination: Destination) -> None:
    print(
        f"{destination.id} | {destination.name} - {destination.city}, {destination.country}"
        f" | {destination.description} | ${destination.base_cost:.2f}"
    )