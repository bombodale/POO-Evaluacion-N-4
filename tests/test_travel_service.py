import unittest
from datetime import date, timedelta
from decimal import Decimal

from viajes_aventura.models import UserRole
from viajes_aventura.repositories import InMemoryRepository
from viajes_aventura.services import TravelService


class TravelServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.service = TravelService(self.repository)
        self.admin = self.service.create_initial_admin(
            "Admin Viajes", "adminviajes", "admin-password-123"
        )

    def test_password_is_hashed_and_username_login_is_case_insensitive(self) -> None:
        self.assertNotEqual(self.admin.password_hash, "admin-password-123")
        authenticated = self.service.authenticate("ADMINVIAJES", "admin-password-123")
        self.assertEqual(authenticated.id, self.admin.id)
        with self.assertRaisesRegex(ValueError, "incorrectos"):
            self.service.authenticate("adminviajes", "wrong-password")

    def test_username_must_be_valid_and_unique_case_insensitively(self) -> None:
        with self.assertRaisesRegex(ValueError, "3 y 30"):
            self.service.register_client("Cliente", "ab", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "solo puede contener"):
            self.service.register_client("Cliente", "cliente uno", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            self.service.register_client("Otro Admin", "ADMINVIAJES", "client-pass-123")

    def test_only_admin_can_manage_destinations(self) -> None:
        client = self.service.register_client("Cliente", "clientuser", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "administrador"):
            self.service.create_destination(client, "Lima", "Peru", "Lima", "Centro", "10")

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
        client = self.service.register_client("Cliente", "clientuser", "client-pass-123")
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
        client = self.service.register_client("Cliente", "clientuser", "client-pass-123")
        with self.assertRaisesRegex(ValueError, "ya no esta disponible"):
            self.service.reserve_package(client, package.id)


if __name__ == "__main__":
    unittest.main()
