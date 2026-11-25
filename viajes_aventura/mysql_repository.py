import os
import re
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Generator

import mysql.connector
from mysql.connector.cursor import MySQLCursor

from .models import Destination, Reservation, TravelPackage, User, UserRole
 

class MySQLRepository:
    """Repositorio MySQL para la base de datos creada en XAMPP."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=False,
        )
        try:
            self._create_schema()
        except Exception:
            self._connection.close()
            raise

    @classmethod
    def from_env(cls) -> "MySQLRepository":
        return cls(
            host=os.getenv("VIAJES_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("VIAJES_DB_PORT", "3306")),
            user=os.getenv("VIAJES_DB_USER", "root"),
            password=os.getenv("VIAJES_DB_PASSWORD", ""),
            database=os.getenv("VIAJES_DB_NAME", "viajes_aventura"),
        )

    def close(self) -> None:
        self._connection.close()

    def _create_schema(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS users (
                id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                username VARCHAR(30) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(16) NOT NULL,
                UNIQUE KEY uq_users_username (username),
                CONSTRAINT chk_users_role CHECK (role IN ('client', 'admin'))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS destinations (
                id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                country VARCHAR(255) NOT NULL,
                city VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                base_cost DECIMAL(12, 2) NOT NULL,
                CONSTRAINT chk_destinations_cost CHECK (base_cost >= 0)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS packages (
                id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                cost DECIMAL(12, 2) NOT NULL,
                CONSTRAINT chk_packages_cost CHECK (cost >= 0),
                CONSTRAINT chk_packages_dates CHECK (end_date >= start_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS package_destinations (
                package_id CHAR(36) NOT NULL,
                destination_id CHAR(36) NOT NULL,
                position INT UNSIGNED NOT NULL,
                PRIMARY KEY (package_id, destination_id),
                UNIQUE KEY uq_package_destination_position (package_id, position),
                CONSTRAINT fk_package_destinations_package
                    FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE RESTRICT,
                CONSTRAINT fk_package_destinations_destination
                    FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id CHAR(36) PRIMARY KEY,
                user_id CHAR(36) NOT NULL,
                package_id CHAR(36) NOT NULL,
                created_at DATETIME(6) NOT NULL,
                CONSTRAINT fk_reservations_user
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
                CONSTRAINT fk_reservations_package
                    FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE RESTRICT,
                INDEX idx_reservations_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        )
        with self._transaction() as cursor:
            for statement in statements:
                cursor.execute(statement)
        self._migrate_users_schema()

    def _migrate_users_schema(self) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'"""
            )
            columns = {row[0]: row[1] for row in cursor.fetchall()}
            username_nullable = columns.get("username") == "YES"
            if "username" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(30) NULL")
                username_nullable = True
            if "email" in columns:
                cursor.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(254) NULL")
                legacy_users_query = (
                    "SELECT id, email FROM users WHERE username IS NULL OR username = ''"
                )
            else:
                legacy_users_query = (
                    "SELECT id, NULL FROM users WHERE username IS NULL OR username = ''"
                )

            cursor.execute(legacy_users_query)
            legacy_users = cursor.fetchall()
            cursor.execute(
                "SELECT username FROM users WHERE username IS NOT NULL AND username <> ''"
            )
            usernames = {row[0].casefold() for row in cursor.fetchall()}
            for user_id, legacy_email in legacy_users:
                local_part = legacy_email.split("@", 1)[0] if legacy_email else "usuario"
                base = re.sub(r"[^a-z0-9_.-]+", "_", local_part.casefold()).strip("._-")
                if len(base) < 3:
                    base = "usuario"
                candidate = base[:30]
                suffix = 1
                while candidate.casefold() in usernames:
                    suffix_text = f"_{suffix}"
                    candidate = f"{base[:30 - len(suffix_text)]}{suffix_text}"
                    suffix += 1
                cursor.execute(
                    "UPDATE users SET username = %s WHERE id = %s",
                    (candidate, user_id),
                )
                usernames.add(candidate.casefold())

            if username_nullable:
                cursor.execute("ALTER TABLE users MODIFY COLUMN username VARCHAR(30) NOT NULL")
            cursor.execute(
                """SELECT INDEX_NAME FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
                     AND COLUMN_NAME = 'username' AND NON_UNIQUE = 0"""
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "ALTER TABLE users ADD UNIQUE KEY uq_users_username (username)"
                )

    @contextmanager
    def _transaction(self) -> Generator[MySQLCursor, None, None]:
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cursor.close()

    def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def add_destination(self, destination: Destination) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """INSERT INTO destinations
                   (id, name, country, city, description, base_cost)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    destination.id,
                    destination.name,
                    destination.country,
                    destination.city,
                    destination.description,
                    destination.base_cost,
                ),
            )

    def update_destination(self, destination: Destination) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """UPDATE destinations
                   SET name = %s, country = %s, city = %s, description = %s, base_cost = %s
                   WHERE id = %s""",
                (
                    destination.name,
                    destination.country,
                    destination.city,
                    destination.description,
                    destination.base_cost,
                    destination.id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("No se encontro el destino.")

    def delete_destination(self, destination_id: str) -> None:
        try:
            with self._transaction() as cursor:
                cursor.execute("DELETE FROM destinations WHERE id = %s", (destination_id,))
                if cursor.rowcount == 0:
                    raise ValueError("No se encontro el destino.")
        except mysql.connector.IntegrityError:
            raise ValueError("No se puede eliminar un destino asociado a un paquete.") from None

    def get_destination(self, destination_id: str) -> Destination | None:
        row = self._fetchone("SELECT * FROM destinations WHERE id = %s", (destination_id,))
        return self._destination_from_row(row) if row else None

    def list_destinations(self) -> list[Destination]:
        rows = self._fetchall("SELECT * FROM destinations ORDER BY name")
        return [self._destination_from_row(row) for row in rows]

    @staticmethod
    def _destination_from_row(row: dict[str, Any]) -> Destination:
        return Destination(
            id=row["id"],
            name=row["name"],
            country=row["country"],
            city=row["city"],
            description=row["description"],
            base_cost=Decimal(row["base_cost"]),
        )

    def add_package(self, package: TravelPackage) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """INSERT INTO packages (id, name, start_date, end_date, cost)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    package.id,
                    package.name,
                    package.start_date,
                    package.end_date,
                    package.cost,
                ),
            )
            cursor.executemany(
                """INSERT INTO package_destinations (package_id, destination_id, position)
                   VALUES (%s, %s, %s)""",
                [
                    (package.id, destination_id, position)
                    for position, destination_id in enumerate(package.destination_ids)
                ],
            )

    def get_package(self, package_id: str) -> TravelPackage | None:
        row = self._fetchone("SELECT * FROM packages WHERE id = %s", (package_id,))
        return self._package_from_row(row) if row else None

    def list_packages(self) -> list[TravelPackage]:
        rows = self._fetchall("SELECT * FROM packages ORDER BY start_date")
        return [self._package_from_row(row) for row in rows]

    def _package_from_row(self, row: dict[str, Any]) -> TravelPackage:
        links = self._fetchall(
            """SELECT destination_id FROM package_destinations
               WHERE package_id = %s ORDER BY position""",
            (row["id"],),
        )
        return TravelPackage(
            id=row["id"],
            name=row["name"],
            start_date=date.fromisoformat(str(row["start_date"])),
            end_date=date.fromisoformat(str(row["end_date"])),
            destination_ids=tuple(link["destination_id"] for link in links),
            cost=Decimal(row["cost"]),
        )

    def add_user(self, user: User) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """INSERT INTO users (id, name, username, password_hash, role)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user.id, user.name, user.username, user.password_hash, user.role.value),
            )

    def get_user_by_username(self, username: str) -> User | None:
        row = self._fetchone("SELECT * FROM users WHERE username = %s", (username,))
        if row is None:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
        )

    def has_user_with_role(self, role: UserRole) -> bool:
        row = self._fetchone("SELECT 1 AS found FROM users WHERE role = %s LIMIT 1", (role.value,))
        return row is not None

    def add_reservation(self, reservation: Reservation) -> None:
        with self._transaction() as cursor:
            cursor.execute(
                """INSERT INTO reservations (id, user_id, package_id, created_at)
                   VALUES (%s, %s, %s, %s)""",
                (
                    reservation.id,
                    reservation.user_id,
                    reservation.package_id,
                    reservation.created_at.astimezone(timezone.utc).replace(tzinfo=None),
                ),
            )

    def list_reservations_for_user(self, user_id: str) -> list[Reservation]:
        rows = self._fetchall(
            """SELECT * FROM reservations WHERE user_id = %s
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return [
            Reservation(
                id=row["id"],
                user_id=row["user_id"],
                package_id=row["package_id"],
                created_at=self._datetime_from_mysql(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def _datetime_from_mysql(value: datetime | str) -> datetime:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
