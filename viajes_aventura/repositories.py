from typing import Protocol

from .models import Destination, Reservation, TravelPackage, User, UserRole


class Repository(Protocol):
    def add_destination(self, destination: Destination) -> None: ...

    def update_destination(self, destination: Destination) -> None: ...

    def delete_destination(self, destination_id: str) -> None: ...

    def get_destination(self, destination_id: str) -> Destination | None: ...

    def list_destinations(self) -> list[Destination]: ...

    def add_package(self, package: TravelPackage) -> None: ...

    def get_package(self, package_id: str) -> TravelPackage | None: ...

    def list_packages(self) -> list[TravelPackage]: ...

    def add_user(self, user: User) -> None: ...

    def get_user_by_username(self, username: str) -> User | None: ...

    def has_user_with_role(self, role: UserRole) -> bool: ...

    def add_reservation(self, reservation: Reservation) -> None: ...

    def list_reservations_for_user(self, user_id: str) -> list[Reservation]: ...


class InMemoryRepository:
    """Repositorio temporal; los datos se pierden al cerrar la aplicacion."""

    def __init__(self) -> None:
        self._destinations: dict[str, Destination] = {}
        self._packages: dict[str, TravelPackage] = {}
        self._users_by_id: dict[str, User] = {}
        self._user_ids_by_username: dict[str, str] = {}
        self._reservations: dict[str, Reservation] = {}

    def add_destination(self, destination: Destination) -> None:
        if destination.id in self._destinations:
            raise ValueError("Ya existe un destino con ese identificador.")
        self._destinations[destination.id] = destination

    def update_destination(self, destination: Destination) -> None:
        if destination.id not in self._destinations:
            raise ValueError("No se encontro el destino.")
        self._destinations[destination.id] = destination

    def delete_destination(self, destination_id: str) -> None:
        if any(destination_id in package.destination_ids for package in self._packages.values()):
            raise ValueError("No se puede eliminar un destino asociado a un paquete.")
        if self._destinations.pop(destination_id, None) is None:
            raise ValueError("No se encontro el destino.")

    def get_destination(self, destination_id: str) -> Destination | None:
        return self._destinations.get(destination_id)

    def list_destinations(self) -> list[Destination]:
        return list(self._destinations.values())

    def add_package(self, package: TravelPackage) -> None:
        if package.id in self._packages:
            raise ValueError("Ya existe un paquete con ese identificador.")
        if any(destination_id not in self._destinations for destination_id in package.destination_ids):
            raise ValueError("El paquete contiene un destino inexistente.")
        self._packages[package.id] = package

    def get_package(self, package_id: str) -> TravelPackage | None:
        return self._packages.get(package_id)

    def list_packages(self) -> list[TravelPackage]:
        return list(self._packages.values())

    def add_user(self, user: User) -> None:
        username_key = user.username.casefold()
        if user.id in self._users_by_id or username_key in self._user_ids_by_username:
            raise ValueError("Ya existe un usuario con ese identificador o nombre de usuario.")
        self._users_by_id[user.id] = user
        self._user_ids_by_username[username_key] = user.id

    def get_user_by_username(self, username: str) -> User | None:
        user_id = self._user_ids_by_username.get(username.casefold())
        return self._users_by_id.get(user_id) if user_id else None

    def has_user_with_role(self, role: UserRole) -> bool:
        return any(user.role == role for user in self._users_by_id.values())

    def add_reservation(self, reservation: Reservation) -> None:
        if reservation.id in self._reservations:
            raise ValueError("Ya existe una reserva con ese identificador.")
        if reservation.user_id not in self._users_by_id:
            raise ValueError("No se encontro el usuario de la reserva.")
        if reservation.package_id not in self._packages:
            raise ValueError("No se encontro el paquete de la reserva.")
        self._reservations[reservation.id] = reservation

    def list_reservations_for_user(self, user_id: str) -> list[Reservation]:
        return [r for r in self._reservations.values() if r.user_id == user_id]
