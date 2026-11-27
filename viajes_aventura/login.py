from getpass import getpass

from .models import User
from .services import TravelService


def login(service: TravelService) -> User | None:
    try:
        return service.authenticate(input("Correo: "), getpass("Contrasena: "))
    except ValueError as error:
        print(f"Error: {error}")
        return None