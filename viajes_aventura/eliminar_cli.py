from .descripcion_cli import show_destinations
from .models import User
from .services import TravelService


def delete_destination(service: TravelService, actor: User) -> None:
    show_destinations(service)
    destination_id = input("ID del destino a eliminar: ").strip()
    service.delete_destination(actor, destination_id)
    print("Destino eliminado.")