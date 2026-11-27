import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from viajes_aventura.crear_cli import create_destination
from viajes_aventura.editar_cli import update_destination
from viajes_aventura.eliminar_cli import delete_destination
from viajes_aventura.models import UserRole
from viajes_aventura.repositories import InMemoryRepository
from viajes_aventura.services import TravelService
from viajes_aventura.sqlite_repository import SQLiteRepository


class TravelServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.service = TravelService(self.repository)
        self.admin = self.service.create_initial_admin(
            "Admin Viajes", "admin@example.com", "admin-password-123"
        )

    def test_password_is_hashed_and_login_is_case_insensitive(self) -> None:
        self.assertNotEqual(self.admin.password_hash, "admin-password-123")
        authenticated = self.service.authenticate("ADMIN@example.com", "admin-password-123")
        self.assertEqual(authenticated.id, self.admin.id)
        with self.assertRaisesRegex(ValueError, "incorrectos"):
            self.service.authenticate("admin@example.com", "wrong-password")

    def test_only_admin_can_manage_destinations(self) -> None:
        client = self.service.register_client("Cliente", "client@example.com", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "administrador"):
            self.service.create_destination(client, "Lima", "Peru", "Lima", "Centro", "10")

    def test_destination_cli_create_update_and_delete(self) -> None:
        with patch(
            "builtins.input",
            side_effect=["Lima", "Peru", "Lima", "Capital", "10.50"],
        ):
            create_destination(self.service, self.admin)

        destination = self.service.list_destinations()[0]
        self.assertEqual(destination.name, "Lima")
        self.assertEqual(destination.base_cost, Decimal("10.50"))

        with patch(
            "builtins.input",
            side_effect=[
                destination.id,
                "Cusco",
                "Peru",
                "Cusco",
                "Andes",
                "20.25",
            ],
        ):
            update_destination(self.service, self.admin)

        updated_destination = self.service.list_destinations()[0]
        self.assertEqual(updated_destination.name, "Cusco")
        self.assertEqual(updated_destination.base_cost, Decimal("20.25"))

        with patch("builtins.input", side_effect=[destination.id]):
            delete_destination(self.service, self.admin)
        self.assertEqual(self.service.list_destinations(), [])

    def test_package_cost_reservation_history_and_delete_guard(self) -> None:
        first = self.service.create_destination(
            self.admin, "Lima", "Peru", "Lima", "Capital", "125.50"
        )
        second = self.service.create_destination(
            self.admin, "Cusco", "Peru", "Cusco", "Andes", "200"
        )
        package = self.service.create_package(
            self.admin,
            "Ruta Peru",
            date.today() + timedelta(days=5),
            date.today() + timedelta(days=10),
            [first.id, second.id],
        )
        self.assertEqual(package.cost, Decimal("325.50"))
        client = self.service.register_client("Cliente", "client@example.com", "client-pass-123")
        self.service.reserve_package(client, package.id)
        history = self.service.reservation_history(client)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1].id, package.id)
        with self.assertRaisesRegex(ValueError, "asociado"):
            self.service.delete_destination(self.admin, first.id)

    def test_rejects_invalid_package_dates_and_duplicate_destination(self) -> None:
        destination = self.service.create_destination(
            self.admin, "Lima", "Peru", "Lima", "Capital", "1"
        )
        with self.assertRaisesRegex(ValueError, "termino"):
            self.service.create_package(
                self.admin,
                "Invalido",
                date.today() + timedelta(days=4),
                date.today(),
                [destination.id],
            )
        with self.assertRaisesRegex(ValueError, "No repitas"):
            self.service.create_package(
                self.admin,
                "Duplicado",
                date.today(),
                date.today(),
                [destination.id, destination.id],
            )

    def test_rejects_past_package_reservation(self) -> None:
        destination = self.service.create_destination(
            self.admin, "Lima", "Peru", "Lima", "Capital", "1"
        )
        package = self.service.create_package(
            self.admin,
            "Pasado",
            date.today() - timedelta(days=2),
            date.today() - timedelta(days=1),
            [destination.id],
        )
        client = self.service.register_client("Cliente", "client@example.com", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "ya no esta disponible"):
            self.service.reserve_package(client, package.id)


class SQLiteRepositoryTests(unittest.TestCase):
    def test_persists_and_reloads_entities_with_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "travel.db"
            repository = SQLiteRepository(database_path)
            service = TravelService(repository)
            admin = service.create_initial_admin(
                "Admin Viajes", "admin@example.com", "admin-password-123"
            )
            destination = service.create_destination(
                admin, "Lima", "Peru", "Lima", "Capital", "123.45"
            )
            package = service.create_package(
                admin,
                "Escapada",
                date.today(),
                date.today() + timedelta(days=2),
                [destination.id],
            )
            with self.assertRaisesRegex(ValueError, "asociado"):
                service.delete_destination(admin, destination.id)
            client = service.register_client(
                "Cliente", "client@example.com", "client-pass-123"
            )
            service.reserve_package(client, package.id)
            repository.close()

            reopened = SQLiteRepository(database_path)
            self.assertEqual(len(reopened.list_destinations()), 1)
            self.assertEqual(reopened.get_package(package.id).cost, Decimal("123.45"))
            self.assertEqual(len(reopened.list_reservations_for_user(client.id)), 1)
            authenticated = TravelService(reopened).authenticate(
                client.email, "client-pass-123"
            )
            self.assertEqual(authenticated.id, client.id)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
