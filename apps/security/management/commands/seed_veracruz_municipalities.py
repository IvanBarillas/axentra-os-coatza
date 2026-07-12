# apps/security/management/commands/seed_veracruz_municipalities.py

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.security.models import Municipality, TenantConfig


VERACRUZ_MUNICIPALITIES = [
    ("001", "Acajete"),
    ("002", "Acatlán"),
    ("003", "Acayucan"),
    ("004", "Actopan"),
    ("005", "Acula"),
    ("006", "Acultzingo"),
    ("007", "Camarón de Tejeda"),
    ("008", "Alpatláhuac"),
    ("009", "Alto Lucero de Gutiérrez Barrios"),
    ("010", "Altotonga"),
    ("011", "Alvarado"),
    ("012", "Amatitlán"),
    ("013", "Naranjos Amatlán"),
    ("014", "Amatlán de los Reyes"),
    ("015", "Ángel R. Cabada"),
    ("016", "La Antigua"),
    ("017", "Apazapan"),
    ("018", "Aquila"),
    ("019", "Astacinga"),
    ("020", "Atlahuilco"),
    ("021", "Atoyac"),
    ("022", "Atzacan"),
    ("023", "Atzalan"),
    ("024", "Tlaltetela"),
    ("025", "Ayahualulco"),
    ("026", "Banderilla"),
    ("027", "Benito Juárez"),
    ("028", "Boca del Río"),
    ("029", "Calcahualco"),
    ("030", "Camerino Z. Mendoza"),
    ("031", "Carrillo Puerto"),
    ("032", "Catemaco"),
    ("033", "Cazones de Herrera"),
    ("034", "Cerro Azul"),
    ("035", "Citlaltépetl"),
    ("036", "Coacoatzintla"),
    ("037", "Coahuitlán"),
    ("038", "Coatepec"),
    ("039", "Coatzacoalcos"),
    ("040", "Coatzintla"),
    ("041", "Coetzala"),
    ("042", "Colipa"),
    ("043", "Comapa"),
    ("044", "Córdoba"),
    ("045", "Cosamaloapan de Carpio"),
    ("046", "Cosautlán de Carvajal"),
    ("047", "Coscomatepec"),
    ("048", "Cosoleacaque"),
    ("049", "Cotaxtla"),
    ("050", "Coxquihui"),
    ("051", "Coyutla"),
    ("052", "Cuichapa"),
    ("053", "Cuitláhuac"),
    ("054", "Chacaltianguis"),
    ("055", "Chalma"),
    ("056", "Chiconamel"),
    ("057", "Chiconquiaco"),
    ("058", "Chicontepec"),
    ("059", "Chinameca"),
    ("060", "Chinampa de Gorostiza"),
    ("061", "Las Choapas"),
    ("062", "Chocamán"),
    ("063", "Chontla"),
    ("064", "Chumatlán"),
    ("065", "Emiliano Zapata"),
    ("066", "Espinal"),
    ("067", "Filomeno Mata"),
    ("068", "Fortín"),
    ("069", "Gutiérrez Zamora"),
    ("070", "Hidalgotitlán"),
    ("071", "Huatusco"),
    ("072", "Huayacocotla"),
    ("073", "Hueyapan de Ocampo"),
    ("074", "Huiloapan de Cuauhtémoc"),
    ("075", "Ignacio de la Llave"),
    ("076", "Ilamatlán"),
    ("077", "Isla"),
    ("078", "Ixcatepec"),
    ("079", "Ixhuacán de los Reyes"),
    ("080", "Ixhuatlán del Café"),
    ("081", "Ixhuatlancillo"),
    ("082", "Ixhuatlán del Sureste"),
    ("083", "Ixhuatlán de Madero"),
    ("084", "Ixmatlahuacan"),
    ("085", "Ixtaczoquitlán"),
    ("086", "Jalacingo"),
    ("087", "Xalapa"),
    ("088", "Jalcomulco"),
    ("089", "Jáltipan"),
    ("090", "Jamapa"),
    ("091", "Jesús Carranza"),
    ("092", "Xico"),
    ("093", "Jilotepec"),
    ("094", "Juan Rodríguez Clara"),
    ("095", "Juchique de Ferrer"),
    ("096", "Landero y Coss"),
    ("097", "Lerdo de Tejada"),
    ("098", "Magdalena"),
    ("099", "Maltrata"),
    ("100", "Manlio Fabio Altamirano"),
    ("101", "Mariano Escobedo"),
    ("102", "Martínez de la Torre"),
    ("103", "Mecatlán"),
    ("104", "Mecayapan"),
    ("105", "Medellín"),
    ("106", "Miahuatlán"),
    ("107", "Las Minas"),
    ("108", "Minatitlán"),
    ("109", "Misantla"),
    ("110", "Mixtla de Altamirano"),
    ("111", "Moloacán"),
    ("112", "Naolinco"),
    ("113", "Naranjal"),
    ("114", "Nautla"),
    ("115", "Nogales"),
    ("116", "Oluta"),
    ("117", "Omealca"),
    ("118", "Orizaba"),
    ("119", "Otatitlán"),
    ("120", "Oteapan"),
    ("121", "Ozuluama de Mascareñas"),
    ("122", "Pajapan"),
    ("123", "Pánuco"),
    ("124", "Papantla"),
    ("125", "Paso del Macho"),
    ("126", "Paso de Ovejas"),
    ("127", "La Perla"),
    ("128", "Perote"),
    ("129", "Platón Sánchez"),
    ("130", "Playa Vicente"),
    ("131", "Poza Rica de Hidalgo"),
    ("132", "Las Vigas de Ramírez"),
    ("133", "Pueblo Viejo"),
    ("134", "Puente Nacional"),
    ("135", "Rafael Delgado"),
    ("136", "Rafael Lucio"),
    ("137", "Los Reyes"),
    ("138", "Río Blanco"),
    ("139", "Saltabarranca"),
    ("140", "San Andrés Tenejapan"),
    ("141", "San Andrés Tuxtla"),
    ("142", "San Juan Evangelista"),
    ("143", "Santiago Tuxtla"),
    ("144", "Sayula de Alemán"),
    ("145", "Soconusco"),
    ("146", "Sochiapa"),
    ("147", "Soledad Atzompa"),
    ("148", "Soledad de Doblado"),
    ("149", "Soteapan"),
    ("150", "Tamalín"),
    ("151", "Tamiahua"),
    ("152", "Tampico Alto"),
    ("153", "Tancoco"),
    ("154", "Tantima"),
    ("155", "Tantoyuca"),
    ("156", "Tatatila"),
    ("157", "Castillo de Teayo"),
    ("158", "Tecolutla"),
    ("159", "Tehuipango"),
    ("160", "Álamo Temapache"),
    ("161", "Tempoal"),
    ("162", "Tenampa"),
    ("163", "Tenochtitlán"),
    ("164", "Teocelo"),
    ("165", "Tepatlaxco"),
    ("166", "Tepetlán"),
    ("167", "Tepetzintla"),
    ("168", "Tequila"),
    ("169", "José Azueta"),
    ("170", "Texcatepec"),
    ("171", "Texhuacán"),
    ("172", "Texistepec"),
    ("173", "Tezonapa"),
    ("174", "Tierra Blanca"),
    ("175", "Tihuatlán"),
    ("176", "Tlacojalpan"),
    ("177", "Tlacolulan"),
    ("178", "Tlacotalpan"),
    ("179", "Tlacotepec de Mejía"),
    ("180", "Tlachichilco"),
    ("181", "Tlalixcoyan"),
    ("182", "Tlalnelhuayocan"),
    ("183", "Tlapacoyan"),
    ("184", "Tlaquilpa"),
    ("185", "Tlilapan"),
    ("186", "Tomatlán"),
    ("187", "Tonayán"),
    ("188", "Totutla"),
    ("189", "Tuxpan"),
    ("190", "Tuxtilla"),
    ("191", "Úrsulo Galván"),
    ("192", "Vega de Alatorre"),
    ("193", "Veracruz"),
    ("194", "Villa Aldama"),
    ("195", "Xoxocotla"),
    ("196", "Yanga"),
    ("197", "Yecuatla"),
    ("198", "Zacualpan"),
    ("199", "Zaragoza"),
    ("200", "Zentla"),
    ("201", "Zongolica"),
    ("202", "Zontecomatlán de López y Fuentes"),
    ("203", "Zozocolco de Hidalgo"),
    ("204", "Agua Dulce"),
    ("205", "El Higo"),
    ("206", "Nanchital de Lázaro Cárdenas del Río"),
    ("207", "Tres Valles"),
    ("208", "Carlos A. Carrillo"),
    ("209", "Tatahuicapan de Juárez"),
    ("210", "Uxpanapa"),
    ("211", "San Rafael"),
    ("212", "Santiago Sochiapan"),
]


class Command(BaseCommand):
    help = "Siembra el catálogo de municipios de Veracruz con claves INEGI/ORFIS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--set-tenant-coatza",
            action="store_true",
            help="Asigna Coatzacoalcos como municipio del TenantConfig activo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🚀 === SEED MUNICIPIOS DE VERACRUZ ==="
            )
        )

        created_count = 0
        updated_count = 0

        for code, name in VERACRUZ_MUNICIPALITIES:
            municipality, created = Municipality.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "state_code": "30",
                    "state_name": "VERACRUZ",
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            if created:
                created_count += 1
                status = "🟢 Creado"
            else:
                updated_count += 1
                status = "🛡️ Actualizado"

            self.stdout.write(f"   {status}: {municipality.code} · {municipality.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Municipios sembrados correctamente. "
                f"Creados: {created_count}. Actualizados: {updated_count}."
            )
        )

        if options["set_tenant_coatza"]:
            self._set_tenant_coatzacoalcos()

    def _set_tenant_coatzacoalcos(self):
        municipality = Municipality.objects.get(code="039")

        tenant = TenantConfig.objects.first()

        if not tenant:
            tenant = TenantConfig.objects.create(
                app_name="Axentra OS",
                entidad_nombre="H. Ayuntamiento Constitucional de Coatzacoalcos",
                siglas="COATZA",
                municipality=municipality,
                rfc="",
                direccion_oficial="",
                primary_color_class="slate-950",
                is_active=True,
                is_deleted=False,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"🏛️ TenantConfig creado y vinculado a {municipality}."
                )
            )
            return

        tenant.municipality = municipality
        tenant.entidad_nombre = "H. Ayuntamiento Constitucional de Coatzacoalcos"
        tenant.siglas = "COATZA"
        tenant.is_active = True
        tenant.is_deleted = False
        tenant.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"🏛️ TenantConfig actualizado y vinculado a {municipality}."
            )
        )
        
