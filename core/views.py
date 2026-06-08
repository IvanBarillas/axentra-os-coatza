# core/views.py
from django.shortcuts import render

def launcher_home_view(request):
    """
    Renderiza la consola general o Launcher de aplicaciones (index.html).
    Esta vista vive en el Core porque funciona como el conmutador global.
    """
    # En el futuro, aquí inicializaremos o limpiaremos variables de contexto de sesión si es necesario
    return render(request, "index.html")