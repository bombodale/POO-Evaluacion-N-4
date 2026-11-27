from decimal import Decimal, InvalidOperation

from .models import User
from .services import TravelService


def create_destination(service: TravelService, actor: User) -> None:
    destination = service.create_destination(
        actor,
        input("Nombre: "),
        input("Pais: "),
        input("Ciudad: "),
        input("Descripcion: "),
        _read_money("Costo base: "),
    )
    print(f"Destino creado: {destination.id}")


def _read_money(prompt: str) -> Decimal:
    raw_value = input(prompt).strip().replace(",", ".")
    try:
        return Decimal(raw_value)
    except InvalidOperation:
        raise ValueError("Ingresa un monto numerico valido.") from None