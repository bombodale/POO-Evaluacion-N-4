import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .models import Destination, Reservation, TravelPackage, User, UserRole


class SQLiteRepository:
    """Adaptador SQLite para guardar las entidades entre ejecuciones."""

    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(str(database_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('client', 'admin'))
            );
            CREATE TABLE IF NOT EXISTS destinations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                description TEXT NOT NULL,
                base_cost TEXT NOT NULL CHECK (CAST(base_cost AS REAL) >= 0)
            );
            CREATE TABLE IF NOT EXISTS packages (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                cost TEXT NOT NULL CHECK (CAST(cost AS REAL) >= 0),
                CHECK (start_date <= end_date)
            );
            CREATE TABLE IF NOT EXISTS package_destinations (
                package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE RESTRICT,
                destination_id TEXT NOT NULL REFERENCES destinations(id) ON DELETE RESTRICT,
                PRIMARY KEY (package_id, destination_id)
            );
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL
            );
            """
        )
        self._connection.commit()

    def add_destination(self, destination: Destination) -> None:
        with self._connection:
            self._connection.execute(
                """INSERT INTO destinations
                   (id, name, country, city, description, base_cost)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    destination.id,
                    destination.name,
                    destination.country,
                    destination.city,
                    destination.description,
                    str(destination.base_cost),
                ),
            )

    def update_destination(self, destination: Destination) -> None:
        with self._connection:
            cursor = self._connection.execute(
                """UPDATE destinations
                   SET name = ?, country = ?, city = ?, description = ?, base_cost = ?
                   WHERE id = ?""",
                (
                    destination.name,
                    destination.country,
                    destination.city,
                    destination.description,
                    str(destination.base_cost),
                    destination.id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("No se encontro el destino.")

    def delete_destination(self, destination_id: str) -> None:
        try:
            with self._connection:
                cursor = self._connection.execute(
                    "DELETE FROM destinations WHERE id = ?", (destination_id,)
                )
                if cursor.rowcount == 0:
                    raise ValueError("No se encontro el destino.")
        except sqlite3.IntegrityError:
            raise ValueError("No se puede eliminar un destino asociado a un paquete.") from None

    def get_destination(self, destination_id: str) -> Destination | None:
        row = self._connection.execute(
            "SELECT * FROM destinations WHERE id = ?", (destination_id,)
        ).fetchone()
        return self._destination_from_row(row) if row else None

    def list_destinations(self) -> list[Destination]:
        rows = self._connection.execute("SELECT * FROM destinations ORDER BY name").fetchall()
        return [self._destination_from_row(row) for row in rows]

    @staticmethod
    def _destination_from_row(row: sqlite3.Row) -> Destination:
        return Destination(
            id=row["id"],
            name=row["name"],
            country=row["country"],
            city=row["city"],
            description=row["description"],
            base_cost=Decimal(row["base_cost"]),
        )

    def add_package(self, package: TravelPackage) -> None:
        with self._connection:
            self._connection.execute(
                """INSERT INTO packages (id, name, start_date, end_date, cost)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    package.id,
                    package.name,
                    package.start_date.isoformat(),
                    package.end_date.isoformat(),
                    str(package.cost),
                ),
            )
            self._connection.executemany(
                """INSERT INTO package_destinations (package_id, destination_id)
                   VALUES (?, ?)""",
                [(package.id, destination_id) for destination_id in package.destination_ids],
            )

    def get_package(self, package_id: str) -> TravelPackage | None:
        row = self._connection.execute(
            "SELECT * FROM packages WHERE id = ?", (package_id,)
        ).fetchone()
        return self._package_from_row(row) if row else None

    def list_packages(self) -> list[TravelPackage]:
        rows = self._connection.execute("SELECT * FROM packages ORDER BY start_date").fetchall()
        return [self._package_from_row(row) for row in rows]

    def _package_from_row(self, row: sqlite3.Row) -> TravelPackage:
        links = self._connection.execute(
            """SELECT destination_id FROM package_destinations
               WHERE package_id = ? ORDER BY rowid""",
            (row["id"],),
        ).fetchall()
        return TravelPackage(
            id=row["id"],
            name=row["name"],
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]),
            destination_ids=tuple(link["destination_id"] for link in links),
            cost=Decimal(row["cost"]),
        )

    def add_user(self, user: User) -> None:
        with self._connection:
            self._connection.execute(
                """INSERT INTO users (id, name, email, password_hash, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (user.id, user.name, user.email, user.password_hash, user.role.value),
            )

    def get_user_by_email(self, email: str) -> User | None:
        row = self._connection.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
        )

    def has_user_with_role(self, role: UserRole) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM users WHERE role = ? LIMIT 1", (role.value,)
        ).fetchone()
        return row is not None

    def add_reservation(self, reservation: Reservation) -> None:
        with self._connection:
            self._connection.execute(
                """INSERT INTO reservations (id, user_id, package_id, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    reservation.id,
                    reservation.user_id,
                    reservation.package_id,
                    reservation.created_at.isoformat(),
                ),
            )

    def list_reservations_for_user(self, user_id: str) -> list[Reservation]:
        rows = self._connection.execute(
            """SELECT * FROM reservations WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        return [
            Reservation(
                id=row["id"],
                user_id=row["user_id"],
                package_id=row["package_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
