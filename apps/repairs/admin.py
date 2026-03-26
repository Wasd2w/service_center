from django.contrib import admin
from .models import Client, Device, Repair, RepairComment, Part


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'phone', 'email', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email']


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['client', 'device_type', 'brand', 'model', 'serial_number']
    list_filter = ['device_type']
    search_fields = ['brand', 'model', 'serial_number']


class PartInline(admin.TabularInline):
    model = Part
    extra = 0


class CommentInline(admin.TabularInline):
    model = RepairComment
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Repair)
class RepairAdmin(admin.ModelAdmin):
    list_display = ['number', 'client', 'status', 'priority', 'master', 'created_at', 'deadline']
    list_filter = ['status', 'priority', 'master']
    search_fields = ['number', 'client__first_name', 'client__last_name', 'client__phone']
    readonly_fields = ['number', 'created_at', 'updated_at', 'completed_at', 'issued_at']
    inlines = [PartInline, CommentInline]
