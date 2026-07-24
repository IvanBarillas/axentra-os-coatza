# apps/shared/management/commands/seed_core_data.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.security.models.accounts import UserProfile
from apps.security.models.organigrama import AreaOperativa, Dependencia, Sede

User = get_user_model()

class Command(BaseCommand):
    help = '🎯 HIDRATACIÓN OPERATIVA ATÓMICA: Siembra el catálogo del Core. Rollback total si algo falla.'

    @transaction.atomic
    def handle(self, *args, **options):
        PASSWORD_GENERICA = "1q2w3e4r5t%"
        
        self.stdout.write(self.style.MIGRATE_HEADING('\n🚀 === INICIANDO HIDRATACIÓN ATÓMICA DEL CORE: AXENTRA OS ==='))

        # =========================================================================
        # 1. SEMBRADO DE SEDES INSTITUCIONALES (INMUEBLES FÍSICOS REALES)
        # =========================================================================
        self.stdout.write(self.style.MIGRATE_HEADING('\n📍 1. REGISTRANDO SEDES INSTITUCIONALES...'))
        
        sedes_data = [
            {"nombre": "PALACIO MUNICIPAL", "direccion": "Zaragoza 404, Centro, Coatzacoalcos"},
            {"nombre": "TESORERIA MUNICIPAL", "direccion": "Quevedo 200, Centro, Coatzacoalcos"},
            {"nombre": "OBRAS PUBLICAS", "direccion": "Malpica 101, Centro, Coatzacoalcos"},
            {"nombre": "FORANEOS", "direccion": "Módulos operativos periféricos de Coatzacoalcos"}
        ]
        
        sedes_creadas = {}
        for s_info in sedes_data:
            sede, creado = Sede.objects.get_or_create(
                nombre=s_info["nombre"],
                defaults={"direccion": s_info["direccion"], "is_active": True}
            )
            sedes_creadas[s_info["nombre"]] = sede
            status = "🟢 Creada" if creado else "🛡️ Verificada"
            self.stdout.write(f"   ↳ {status}: {sede.nombre} (ID: {sede.id})")

        # =========================================================================
        # 2. SEMBRADO DE DEPENDENCIAS Y ÁREAS MATRICIALES (TOPOLOGÍA DE SEGREGACIÓN)
        # =========================================================================
        self.stdout.write(self.style.MIGRATE_HEADING('\n🏛️ 2. ESTRUCTURANDO DEPARTAMENTOS MATRICIALES (ÁREAS CONTROLADAS)...'))
        
        organigrama_matriz = {
            "INNOVACION GUBERNAMENTAL": {
                "areas": ["SOPORTE TECNICO", "PROYECTOS", "WEBMASTER", "INFRAESTRUCTURA", "DESARROLLO"]
            },
            "RECURSOS HUMANOS": {
                "areas": ["CHEQUES", "PERMISOS Y ASISTENCIAS", "CAPACITACION"]
            },
            "DIRECCION DE EGRESOS": {
                "areas": ["PAGOS", "DISPERSIONES VARIAS", "PROVEEDORES"]
            },
            "PATRIMONIO MUNICIPAL": {
                "areas": ["PARQUE VEHICULAR", "CAPTURISTA"]
            },
        }

        areas_creadas_map = {}
        for dep_nombre, data in organigrama_matriz.items():
            dependencia, _ = Dependencia.objects.get_or_create(
                nombre=dep_nombre,
                defaults={"is_active": True}
            )
            self.stdout.write(f"  🏢 Dependencia: [{dependencia.nombre}]")

            for area_nombre in data["areas"]:
                # 🪐 REGLA RESTRICCIONES SOBERANA:
                # Si el área es SOPORTE TECNICO, se clona en todas las sedes físicas.
                # De lo contrario, se inicializa exclusivamente en la central (TESORERIA MUNICIPAL).
                if area_nombre == "SOPORTE TECNICO":
                    sedes_a_vincular = sedes_creadas.items()
                else:
                    sedes_a_vincular = [("TESORERIA MUNICIPAL", sedes_creadas["TESORERIA MUNICIPAL"])]

                for sede_nombre, sede_obj in sedes_a_vincular:
                    area, creado_area = AreaOperativa.objects.get_or_create(
                        dependencia=dependencia,
                        nombre=area_nombre,
                        sede_fisica=sede_obj,
                        defaults={"is_active": True}
                    )
                    key_compuesta = f"{area_nombre}@{sede_nombre}"
                    areas_creadas_map[key_compuesta] = area

        # =========================================================================
        # 3. HIDRATACIÓN DE LA PLANTILLA DE PERSONAL REAL (EXPEDIENTES CUADRÍCULA)
        # =========================================================================
        self.stdout.write(self.style.MIGRATE_HEADING('\n👥 3. CARGANDO PLANTILLA REAL DE PERSONAL...'))

        personal_oficial = [
            {"nombre": "MARIO IVAN GONZALEZ BARILLAS", "email": "mario.ivan@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "SOPORTE TECNICO", "puesto": "Coordinador de Soporte"},
            {"nombre": "VERONICA PINTO", "email": "veronica.pinto@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "SOPORTE TECNICO", "puesto": "Técnico de Soporte"},
            {"nombre": "VERONICA IXBA", "email": "veronica.ixba@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "SOPORTE TECNICO", "puesto": "Técnico de Soporte"},
            {"nombre": "FRANCISCO MARTINEZ VILLASECA", "email": "francisco.martinez@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "SOPORTE TECNICO", "puesto": "Técnico de Soporte"},
            {"nombre": "HUGO ARMANDO NAVA", "email": "hugo.nava@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "WEBMASTER", "puesto": "Administrador Web Core"},
            {"nombre": "MIGUEL NARVAEZ", "email": "miguel.narvaez@gmail.com", "sede": "OBRAS PUBLICAS", "area_key": "SOPORTE TECNICO", "puesto": "Técnico de Soporte Extensión"},
            {"nombre": "GABRIEL JUAREZ ROLDAN", "email": "gabriel.juarez@gmail.com", "sede": "PALACIO MUNICIPAL", "area_key": "SOPORTE TECNICO", "puesto": "Técnico Residente Palacio"},
            {"nombre": "GUILLERMO MAYO", "email": "guillermo.mayo@gmail.com", "sede": "FORANEOS", "area_key": "SOPORTE TECNICO", "puesto": "Soporte Módulos Foráneos"},
            {"nombre": "PATRIMONNIO MUNICIPAL", "email": "pat@gmail.com", "sede": "TESORERIA MUNICIPAL", "area_key": "CAPTURISTA", "puesto": "Administrador de Patrimonio"},
        ]

        for emp in personal_oficial:
            partes = emp["nombre"].split(" ", 1)
            f_name = partes[0]
            l_name = partes[1] if len(partes) > 1 else ""

            key_busqueda = f"{emp['area_key']}@{emp['sede']}"
            area_obj = areas_creadas_map.get(key_busqueda)

            # 🚨 CONTROL DE INTEGRIDAD CRÍTICO: Rollback completo si falta un área o si el mapeo está roto
            if not area_obj:
                raise CommandError(
                    f"💥 [ROLLBACK EN CALIENTE] Falló la integridad del Core. "
                    f"La celda relacional '{key_busqueda}' no existe en el catálogo filtrado de sedes. "
                    f"Operación cancelada de inmediato."
                )

            f_user, f_created = User.objects.get_or_create(
                email=emp["email"],
                defaults={
                    "first_name": f_name, 
                    "last_name": l_name,
                    "is_staff": True, 
                    "is_superuser": False, 
                    "is_active": True,
                    "is_email_verified": True if hasattr(User, 'is_email_verified') else False
                }
            )

            if f_created:
                f_user.set_password(PASSWORD_GENERICA)
                f_user.save()
                user_status = "🟢 Creado"
            else:
                user_status = "🛡️ Verificado"

            profile_obj, profile_created = UserProfile.objects.get_or_create(
                user=f_user,
                defaults={
                    "area": area_obj,
                    "puesto": emp.get("puesto", "Servidor Público")
                }
            )
            
            if not profile_created:
                profile_obj.area = area_obj
                profile_obj.puesto = emp.get("puesto", "Servidor Público")
                profile_obj.save()

            self.stdout.write(f"   👤 {user_status}: {f_user.get_full_name()} ➔ [{key_busqueda}]")

        self.stdout.write(self.style.SUCCESS('\n🔒 === INTEGRIDAD PERFECTA: TRANSACCION CONFIRMADA SIN ÁREAS DUPLICADAS ===\n'))