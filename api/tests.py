from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ordenes.models import Cliente, Orden


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="authuser",
            password="pass1234",
            first_name="Auth",
            last_name="User",
        )

    def test_login_sets_http_only_cookies(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "authuser", "password": "pass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Login exitoso")
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_can_be_read_and_updated_with_cookie_auth(self):
        self.client.post(
            reverse("token_obtain_pair"),
            {"username": "authuser", "password": "pass1234"},
            format="json",
        )

        response = self.client.patch(
            reverse("profile"),
            {"first_name": "Updated", "email": "updated@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "updated@example.com")


class ClienteApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="pass1234")
        self.client.force_authenticate(self.user)

    def test_create_and_search_cliente(self):
        response = self.client.post(
            reverse("clientes-list"),
            {
                "nombre": "Juan",
                "apellido": "Perez",
                "dni": "30111222",
                "email": "juan@example.com",
                "celular": "1122334455",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse("clientes-list"), {"search": "30111222"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Juan")

    def test_cliente_delete_is_blocked(self):
        cliente = Cliente.objects.create(nombre="Ana", apellido="Gomez")

        response = self.client.delete(reverse("clientes-detail", args=[cliente.id]))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Cliente.objects.filter(id=cliente.id).exists())


class OrdenApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tech", password="pass1234")
        self.client.force_authenticate(self.user)
        self.cliente = Cliente.objects.create(
            nombre="Lucas",
            apellido="Diaz",
            dni="33111222",
            celular="1133445566",
        )

    def test_create_order_assigns_creator_and_pending_state(self):
        response = self.client.post(
            reverse("ordenes-list"),
            {
                "cliente_id": self.cliente.id,
                "dispositivo_tipo": "Celular",
                "marca": "Samsung",
                "modelo": "A54",
                "falla_reportada": "No enciende",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        orden = Orden.objects.get(id=response.data["id"])
        self.assertEqual(orden.creado_por, self.user)
        self.assertEqual(orden.estado, Orden.Estado.PENDIENTE)
        self.assertEqual(str(orden.public_token), response.data["public_token"])

    def test_order_state_transition_validates_required_budget(self):
        orden = Orden.objects.create(
            cliente=self.cliente,
            creado_por=self.user,
            marca="Motorola",
            modelo="G9",
        )

        response = self.client.patch(
            reverse("ordenes-cambiar-estado", args=[orden.id]),
            {"estado": Orden.Estado.DIAGNOSTICADO},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            reverse("ordenes-cambiar-estado", args=[orden.id]),
            {
                "estado": Orden.Estado.DIAGNOSTICADO,
                "presupuesto": "25000.00",
                "senia": "5000.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, Orden.Estado.DIAGNOSTICADO)
        self.assertEqual(str(orden.presupuesto), "25000.00")

    def test_order_list_hides_lock_value(self):
        orden = Orden.objects.create(
            cliente=self.cliente,
            creado_por=self.user,
            marca="Samsung",
            modelo="A32",
            bloqueo_tipo=Orden.BloqueoTipo.PIN,
            bloqueo_valor="1234",
        )

        list_response = self.client.get(reverse("ordenes-list"))
        detail_response = self.client.get(reverse("ordenes-detail", args=[orden.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertNotIn("bloqueo_valor", list_response.data["results"][0])
        self.assertEqual(list_response.data["results"][0]["bloqueo_resumen"], "PIN cargado")

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["bloqueo_valor"], "1234")

    def test_public_tracking_endpoint_does_not_require_authentication(self):
        orden = Orden.objects.create(
            cliente=self.cliente,
            creado_por=self.user,
            marca="Apple",
            modelo="iPhone 12",
            falla_reportada="Pantalla rota",
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("public-orden", kwargs={"token": orden.public_token})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["orden_id"], orden.id)
        self.assertEqual(response.data["cliente"]["nombre"], "Lucas")
        self.assertEqual(response.data["equipo"]["marca"], "Apple")
