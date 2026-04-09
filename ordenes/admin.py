from django.contrib import admin
from .models import Cliente, Orden, OrdenFoto


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id", "apellido", "nombre", "dni", "celular", "email")
    search_fields = ("nombre", "apellido", "dni", "celular", "email")


class OrdenFotoInline(admin.TabularInline):
    model = OrdenFoto
    extra = 0


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    inlines = [OrdenFotoInline]
    list_display = ("id", "estado", "cliente", "marca", "modelo", "created_at")
    list_filter = ("estado",)
    search_fields = ("id", "cliente__nombre", "cliente__apellido", "marca", "modelo", "imei_serial")
