from decimal import Decimal, InvalidOperation

from .descripcion_cli import show_destinations
from .models import User
from .services import TravelService


def update_destination(service: TravelService, actor: User) -> None:
    show_destinations(service)
    destination_id = input("ID del destino a modificar: ").strip()
    destination = service.update_destination(
        actor,
        destination_id,
        input("Nuevo nombre: "),
        input("Nuevo pais: "),
        input("Nueva ciudad: "),
        input("Nueva descripcion: "),
        _read_money("Nuevo costo base: "),
    )
    print(f"Destino actualizado: {destination.name}")


def _read_money(prompt: str) -> Decimal:
    raw_value = input(prompt).strip().replace(",", ".")
    try:
        return Decimal(raw_value)
    except InvalidOperation:
        raise ValueError("Ingresa un monto numerico valido.") from None