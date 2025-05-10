# braynr_demo/urls.py
from django.urls import path
from . import views  # Importa le views dalla stessa directory (braynr_demo)

app_name = 'braynr_demo'

urlpatterns = [
    # URL radice dell'app braynr_demo
    path('', views.main_braynr_view, name='main_braynr'),
    path('rubber-duck/', views.rubber_duck_view, name='rubber_duck'),
    path('simplify/', views.simplify_view, name='simplify'),
    path('scheduler/', views.scheduler_view, name='scheduler'),
    # Aggiungi altri path per le altre feature qui
]
