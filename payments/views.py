from django.shortcuts import render
from .forms import PaymentSignInForm


# Create your views here.
def choose_user(request):
    form = PaymentSignInForm()
    return render(request, 'choose_user.html', {'form': form})