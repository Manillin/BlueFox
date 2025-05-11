# braynr_demo/urls.py
from django.urls import path
from . import views  # Importa le views dalla stessa directory (braynr_demo)

app_name = 'braynr_demo'

urlpatterns = [
    # URL radice dell'app braynr_demo
    path('', views.main_braynr_view, name='main_braynr'),
    path('rubber_duck/', views.rubber_duck_view, name='rubber_duck_page'),
    path('process_pdf/', views.process_pdf_view, name='process_pdf'),
    path('process_audio/', views.process_rubber_duck_audio, name='process_audio'),
    path('simplify/', views.simplify_view, name='simplify'),
    path('scheduler/', views.scheduler_view, name='scheduler'),

    # Nuovi URL per il Planner
    path('planner/', views.planner_page_view, name='planner_page'),
    path('generate_plan/', views.generate_study_plan_view,
         name='generate_study_plan'),
]
