from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.


def main_braynr_view(request):
    return HttpResponse("Ciao! Questa è la pagina principale di Braynr. Da qui potrai accedere alle varie feature.")


def rubber_duck_view(request):
    return HttpResponse("Ciao! Feature: Rubber Duck Method.")


def simplify_view(request):
    return HttpResponse("Ciao! Feature: Simplify Problem.")


def scheduler_view(request):
    return HttpResponse("Ciao! Feature: Scheduler.")

# Definisci le altre funzioni view per le tue feature qui
