# apps/security/models/accounts.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings

class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico institucional es obligatorio.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_manager', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe declarar is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe declarar is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Identidad digital inmutable del funcionario público dentro de Axentra OS."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Autenticación exclusiva por Email
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    must_change_password = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    is_manager = models.BooleanField(
        default=False, 
        help_text='Indica si el usuario cuenta con inmunidad jerárquica y bypass global en la plataforma.'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_admin_user(self):
        return any([self.is_staff, self.is_superuser, self.is_manager])

    class Meta:
        db_table = 'axentra_core_users'
        ordering = ['-created_at']
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self) -> str:
        """Representación oficial en selectores y formularios de Axentra OS."""
        if self.first_name or self.last_name:
            nombre_completo = f"{self.first_name} {self.last_name}".strip()
            return f"{nombre_completo} ({self.email})"
        return self.email


class UserProfile(models.Model):
    """Expediente laboral de adscripción geográfica y administrativa del funcionario."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 🟢 CORRECCIÓN: Alineado con la telemetría del decorador (request.user.axentra_profile)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="axentra_profile",
        verbose_name="Usuario"
    )
    
    area = models.ForeignKey(
        'security.AreaOperativa', 
        on_delete=models.PROTECT, 
        related_name="empleados",
        verbose_name="Área Operativa / Oficina de Adscripción"
    )
    
    puesto = models.CharField("Puesto del Funcionario", max_length=100, blank=True, help_text="Ej: Jefa de Departamento, Auditor Interno")
    telefono_oficina = models.CharField("Teléfono de Oficina / Extensión", max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🟢 NUEVA PROPIEDAD: Resuelve el puente roto con el decorador de seguridad
    @property
    def is_root_admin(self) -> bool:
        """Determina si el usuario amparado en este perfil cuenta con bypass de administración superior."""
        return self.user.is_superuser or self.user.is_manager

    @property
    def dependencia(self):
        """Resuelve en caliente la Dirección General de adscripción leyendo la matriz."""
        return self.area.dependencia if self.area else None

    @property
    def sede(self):
        """Resuelve en caliente el inmueble físico donde trabaja el empleado leyendo la matriz."""
        return self.area.sede_fisica if self.area else None

    class Meta:
        db_table = 'axentra_core_user_profiles'
        verbose_name = "Perfil de Funcionario"
        verbose_name_plural = "Perfiles de Funcionarios"

    def __str__(self):
        return f"{self.user.full_name} - {self.puesto or 'Sin Puesto Asignado'}"