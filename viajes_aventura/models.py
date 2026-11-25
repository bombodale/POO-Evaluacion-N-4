from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class UserRole(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"


class User:
    def __init__(
        self, id: str, name: str, username: str, password_hash: str, role: UserRole
    ) -> None:
        self.id = id
        self.name = name
        self.username = username
        self.password_hash = password_hash
        self.role = role


class Destination:
    def __init__(
        self,
        id: str,
        name: str,
        country: str,
        city: str,
        description: str,
        base_cost: Decimal,
    ) -> None:
        self.id = id
        self.name = name
        self.country = country
        self.city = city
        self.description = description
        self.base_cost = base_cost


class TravelPackage:
    def __init__(
        self,
        id: str,
        name: str,
        start_date: date,
        end_date: date,
        destination_ids: tuple[str, ...],
        cost: Decimal,
    ) -> None:
        self.id = id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.destination_ids = destination_ids
        self.cost = cost


class Reservation:
    def __init__(self, id: str, user_id: str, package_id: str, created_at: datetime) -> None:
        self.id = id
        self.user_id = user_id
        self.package_id = package_id
        self.created_at = created_at
