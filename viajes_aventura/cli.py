from collections.abc import Callable
from datetime import date
from getpass import getpass
from pathlib import Path

from .crear_cli import create_destination
from .descripcion_cli import show_destinations
from .editar_cli import update_destination
from .eliminar_cli import delete_destination
from .login import login
from .models import TravelPackage, User, UserRole
from .services import TravelService
from .sqlite_repository import SQLiteRepository


def main() -> None:
    database_directory = Path.home() / ".viajes_aventura"
    database_directory.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRepository(database_directory / "viajes_aventura.db")
    try:
        _run_application(TravelService(repository))
    finally:
        repository.close()


def _run_application(service: TravelService) -> None:
    print("=== Viajes Aventura ===")
    if not service.repository.has_user_with_role(UserRole.ADMIN):
        print("Configuracion inicial: crea la cuenta del administrador.")
        try:
            _create_account(service, admin=True)
        except ValueError as error:
            print(f"Error: {error}")
            return

    while True:
        print("\n1. Iniciar sesion\n2. Registrarme como cliente\n0. Salir")
        option = input("Opcion: ").strip()
        if option == "0":
            return
        if option == "2":
            _run_action(lambda: _create_account(service, admin=False))
            continue
        if option == "1":
            user = login(service)
            if user:
                _user_menu(service, user)
            continue
        print("Selecciona una opcion valida.")


def _create_account(service: TravelService, admin: bool) -> None:
    name = input("Nombre: ")
    email = input("Correo: ")
    password = getpass("Contrasena (minimo 10 caracteres): ")
    if admin:
        service.create_initial_admin(name, email, password)
        print("Administrador creado. Esta cuenta se conserva entre ejecuciones.")
    else:
        service.register_client(name, email, password)
        print("Cuenta de cliente creada.")


def _user_menu(service: TravelService, user: User) -> None:
    print(f"\nBienvenido/a, {user.name}.")
    while True:
        if user.role == UserRole.ADMIN:
            print(
                "\n1. Listar destinos\n2. Registrar destino\n3. Modificar destino"
                "\n4. Eliminar destino\n5. Crear paquete\n6. Listar paquetes\n0. Cerrar sesion"
            )
            option = input("Opcion: ").strip()
            actions = {
                "1": lambda: show_destinations(service),
                "2": lambda: create_destination(service, user),
                "3": lambda: update_destination(service, user),
                "4": lambda: delete_destination(service, user),
                "5": lambda: _create_package(service, user),
                "6": lambda: _show_packages(service),
            }
        else:
            print(
                "\n1. Listar destinos\n2. Listar paquetes\n3. Reservar paquete"
                "\n4. Historial de reservas\n0. Cerrar sesion"
            )
            option = input("Opcion: ").strip()
            actions = {
                "1": lambda: show_destinations(service),
                "2": lambda: _show_packages(service),
                "3": lambda: _reserve_package(service, user),
                "4": lambda: _show_history(service, user),
            }
        if option == "0":
            return
        action = actions.get(option)
        if action is None:
            print("Selecciona una opcion valida.")
        else:
            _run_action(action)


def _create_package(service: TravelService, actor: User) -> None:
    show_destinations(service)
    destination_ids = [
        item.strip()
        for item in input("IDs de destinos separados por coma: ").split(",")
        if item.strip()
    ]
    package = service.create_package(
        actor,
        input("Nombre del paquete: "),
        _read_date("Fecha de inicio (AAAA-MM-DD): "),
        _read_date("Fecha de termino (AAAA-MM-DD): "),
        destination_ids,
    )
    print(f"Paquete creado: {package.id} | Costo calculado: ${package.cost:.2f}")


def _show_packages(service: TravelService) -> None:
    packages = service.list_packages()
    if not packages:
        print("Todavia no hay paquetes registrados.")
        return
    for package in packages:
        _print_package(service, package)


def _print_package(service: TravelService, package: TravelPackage) -> None:
    destination_names = {
        destination.id: destination.name for destination in service.list_destinations()
    }
    names = ", ".join(destination_names.get(item, item) for item in package.destination_ids)
    print(
        f"{package.id} | {package.name} | {package.start_date} al {package.end_date}"
        f" | {names} | ${package.cost:.2f}"
    )


def _reserve_package(service: TravelService, user: User) -> None:
    _show_packages(service)
    reservation = service.reserve_package(user, input("ID del paquete a reservar: ").strip())
    print(f"Reserva confirmada: {reservation.id}")


def _show_history(service: TravelService, user: User) -> None:
    history = service.reservation_history(user)
    if not history:
        print("No tienes reservas registradas.")
        return
    for reservation, package in history:
        print(
            f"{reservation.created_at:%Y-%m-%d %H:%M UTC} | {package.name}"
            f" | {package.start_date} al {package.end_date} | ${package.cost:.2f}"
        )


def _read_date(prompt: str) -> date:
    try:
        return date.fromisoformat(input(prompt).strip())
    except ValueError:
        raise ValueError("Ingresa una fecha valida con formato AAAA-MM-DD.") from None


def _run_action(action: Callable[[], None]) -> None:
    try:
        action()
    except ValueError as error:
        print(f"Error: {error}")
