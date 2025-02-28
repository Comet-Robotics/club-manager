from django.shortcuts import render
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.views.decorators.http import require_GET
from django.conf import settings
from events.models import Attendance
from django.views.generic import ListView
from django.http import HttpResponseRedirect


from .forms import UserProfileForm, UserForm

# Create your views here.
def profile_view(request):
    user = request.user
    
    user_form = UserForm(instance=user)
    profile_form = UserProfileForm(instance=user.userprofile)
    
    if request.method == "POST":
        if 'user' in request.POST:
           user_form = UserForm(request.POST, instance=user)
           if user_form.is_valid():
               user_form.save()
        if 'profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user.userprofile)
            if profile_form.is_valid():
                profile_form.save()
      
    
    return render(request, 'profile.html', {'user': user, "profile_form": profile_form, "user_form": user_form})

class AttendanceListView(ListView):
    model = Attendance
    template_name = 'profile_fragments/attendance_list.html'
    paginate_by = 5
    context_object_name = 'attendances'
    
    def get_queryset(self):
        return Attendance.objects.order_by('-timestamp').filter(user=self.request.user)

def spa_view(request):
    return render(request, 'spa.html', {'DEBUG': settings.DEBUG})

@require_GET
def apple_merchant_id(request):
    lines = [
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def index(request):
    return HttpResponsePermanentRedirect('/_/')
