import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from .models import Destination, Reservation, TravelPackage, User, UserRole
from .repositories import InMemoryRepository, Repository
from .security import hash_password, verify_password


class TravelService:
    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository if repository is not None else InMemoryRepository()

    def register_client(self, name: str, email: str, password: str) -> User:
        return self._register_user(name, email, password, UserRole.CLIENT)

    def create_initial_admin(self, name: str, email: str, password: str) -> User:
        if self.repository.has_user_with_role(UserRole.ADMIN):
            raise ValueError("Ya existe un administrador.")
        return self._register_user(name, email, password, UserRole.ADMIN)

    def _register_user(self, name: str, email: str, password: str, role: UserRole) -> User:
        clean_name = self._required_text(name, "nombre")
        clean_email = email.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean_email):
            raise ValueError("El correo electronico no tiene un formato valido.")
        if len(password) < 10:
            raise ValueError("La contrasena debe tener al menos 10 caracteres.")
        if self.repository.get_user_by_email(clean_email):
            raise ValueError("Ya existe una cuenta con ese correo.")
        user = User(
            id=str(uuid.uuid4()),
            name=clean_name,
            email=clean_email,
            password_hash=hash_password(password),
            role=role,
        )
        self.repository.add_user(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.repository.get_user_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("Correo o contrasena incorrectos.")
        return user

    def create_destination(
        self,
        actor: User,
        name: str,
        country: str,
        city: str,
        description: str,
        base_cost: str | Decimal,
    ) -> Destination:
        self._require_admin(actor)
        destination = Destination(
            id=str(uuid.uuid4()),
            name=self._required_text(name, "nombre"),
            country=self._required_text(country, "pais"),
            city=self._required_text(city, "ciudad"),
            description=self._required_text(description, "descripcion"),
            base_cost=self._money(base_cost),
        )
        self.repository.add_destination(destination)
        return destination

    def update_destination(
        self,
        actor: User,
        destination_id: str,
        name: str,
        country: str,
        city: str,
        description: str,
        base_cost: str | Decimal,
    ) -> Destination:
        self._require_admin(actor)
        if self.repository.get_destination(destination_id) is None:
            raise ValueError("No se encontro el destino.")
        destination = Destination(
            id=destination_id,
            name=self._required_text(name, "nombre"),
            country=self._required_text(country, "pais"),
            city=self._required_text(city, "ciudad"),
            description=self._required_text(description, "descripcion"),
            base_cost=self._money(base_cost),
        )
        self.repository.update_destination(destination)
        return destination

    def delete_destination(self, actor: User, destination_id: str) -> None:
        self._require_admin(actor)
        self.repository.delete_destination(destination_id)

    def list_destinations(self) -> list[Destination]:
        return self.repository.list_destinations()

    def create_package(
        self,
        actor: User,
        name: str,
        start_date: date,
        end_date: date,
        destination_ids: list[str],
    ) -> TravelPackage:
        self._require_admin(actor)
        if not destination_ids:
            raise ValueError("Selecciona al menos un destino.")
        if len(destination_ids) != len(set(destination_ids)):
            raise ValueError("No repitas destinos en el paquete.")
        if end_date < start_date:
            raise ValueError("La fecha de termino no puede ser anterior a la fecha de inicio.")
        destinations = [self.repository.get_destination(item) for item in destination_ids]
        if any(destination is None for destination in destinations):
            raise ValueError("Uno o mas destinos no existen.")
        total = sum(
            (destination.base_cost for destination in destinations if destination is not None),
            start=Decimal("0.00"),
        )
        package = TravelPackage(
            id=str(uuid.uuid4()),
            name=self._required_text(name, "nombre del paquete"),
            start_date=start_date,
            end_date=end_date,
            destination_ids=tuple(destination_ids),
            cost=total,
        )
        self.repository.add_package(package)
        return package

    def list_packages(self) -> list[TravelPackage]:
        return self.repository.list_packages()

    def reserve_package(self, actor: User, package_id: str) -> Reservation:
        if actor.role != UserRole.CLIENT:
            raise ValueError("Solo un cliente puede realizar reservas.")
        package = self.repository.get_package(package_id)
        if package is None:
            raise ValueError("No se encontro el paquete.")
        if package.start_date < date.today():
            raise ValueError("El paquete ya no esta disponible porque su fecha de inicio paso.")
        reservation = Reservation(
            id=str(uuid.uuid4()),
            user_id=actor.id,
            package_id=package.id,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.add_reservation(reservation)
        return reservation

    def reservation_history(self, actor: User) -> list[tuple[Reservation, TravelPackage]]:
        if actor.role != UserRole.CLIENT:
            raise ValueError("Solo un cliente puede consultar su historial.")
        history: list[tuple[Reservation, TravelPackage]] = []
        for reservation in self.repository.list_reservations_for_user(actor.id):
            package = self.repository.get_package(reservation.package_id)
            if package is not None:
                history.append((reservation, package))
        return history

    @staticmethod
    def _require_admin(actor: User) -> None:
        if actor.role != UserRole.ADMIN:
            raise ValueError("Esta operacion requiere una cuenta de administrador.")

    @staticmethod
    def _required_text(value: str, field: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError(f"El campo {field} es obligatorio.")
        return clean_value

    @staticmethod
    def _money(value: str | Decimal) -> Decimal:
        try:
            amount = Decimal(value)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("El costo debe ser un monto numerico valido.") from None
        if not amount.is_finite() or amount < 0:
            raise ValueError("El costo debe ser un monto mayor o igual a cero.")
        try:
            return amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            raise ValueError("El costo esta fuera del rango permitido.") from None
