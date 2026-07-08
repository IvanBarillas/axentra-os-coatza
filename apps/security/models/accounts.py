# apps/security/models/accounts.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from apps.shared.models import AxentraBaseModel

class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email: raise ValueError("El correo electrónico institucional es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_manager", True)
        if extra_fields.get("is_staff") is not True: raise ValueError("Superuser debe declarar is_staff=True.")
        if extra_fields.get("is_superuser") is not True: raise ValueError("Superuser debe declarar is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Identidad digital inmutable del funcionario público dentro de Axentra OS."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    must_change_password = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    is_manager = models.BooleanField(default=False, help_text="Indica si el usuario cuenta con inmunidad jerárquica y bypass global.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    @property
    def full_name(self): return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin_user(self): return any([self.is_staff, self.is_superuser, self.is_manager])

    class Meta:
        db_table = "axentra_core_users"
        ordering = ["-created_at"]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})" if self.first_name or self.last_name else self.email

class UserProfile(AxentraBaseModel):
    """Expediente laboral de adscripción geográfica y administrativa del funcionario."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="axentra_profile", verbose_name="Usuario")
    area = models.ForeignKey("security.AreaOperativa", on_delete=models.PROTECT, related_name="empleados", verbose_name="Área Operativa / Oficina de Adscripción")
    puesto = models.CharField("Puesto del Funcionario", max_length=100, blank=True, help_text="Ej: Jefa de Departamento, Auditor Interno")
    telefono_oficina = models.CharField("Teléfono de Oficina / Extensión", max_length=20, blank=True)

    @property
    def is_root_admin(self) -> bool: return self.user.is_superuser or self.user.is_manager

    @property
    def dependencia(self): return self.area.dependencia if self.area else None

    @property
    def sede(self): return self.area.sede_fisica if self.area else None

    class Meta:
        db_table = "axentra_core_user_profiles"
        verbose_name = "Perfil de Funcionario"
        verbose_name_plural = "Perfiles de Funcionarios"

    def __str__(self): return f"{self.user.full_name} - {self.puesto or 'Sin Puesto Asignado'}"