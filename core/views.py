from django.shortcuts import render

# Create your views here.
def profile_view(request):
    user = request.user
    return render(request, 'profile.html', {'user': user})
