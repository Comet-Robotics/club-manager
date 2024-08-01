from django.shortcuts import render, redirect
from django.http import Http404
from .forms import SignInForm, CreateProfileForm, UserSearchForm
from .models import UserIdentification, Attendance, Event
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from .tables import UserTable

@staff_member_required
def sign_in(request):
    events = Event.objects.all()
    if request.method == 'POST': 
        form = SignInForm(request.POST)
        event_field = request.POST['event'] 
        current_event = Event.objects.get(pk=event_field)
        if form.is_valid():
            student_id = form.cleaned_data['card_data']            
            try:
                user_profile = UserIdentification.objects.get(student_id=student_id)
                if user_profile:
                    form = SignInForm()
                    status, created = Attendance.objects.get_or_create(event=current_event, user=user_profile.user)
                    if created:
                        message = ("success")
                    else:
                        message = ("repeat")
            except UserIdentification.DoesNotExist:
                return redirect('create-profile', student_id=student_id)
            
            return render(request, 'sign_in.html', {'form': form, 'message': message, 'status': status, 'user': user_profile.user, 'events': events})

    else:
        form = SignInForm()

    return render(request, 'sign_in.html', {'form': form, 'events': events})

@staff_member_required
def create_profile(request, student_id):
    if request.method == 'POST':
        form = CreateProfileForm(request.POST)
        if form.is_valid():
            net_id = form.cleaned_data['net_id']
            first = form.cleaned_data['first_name']
            last = form.cleaned_data['last_name']
            UserIdentification.create_extended_user(net_id=net_id, student_id=student_id, first=first, last=last)
            return redirect('sign_in')
    else:
        form = CreateProfileForm()

    return render(request, 'create_profile.html', {'form': form})

@staff_member_required
def lookup_user(request):
    users = []
    if request.method == 'POST':
        form = UserSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['search']
            users = User.objects.filter(first_name__icontains=query) | User.objects.filter(last_name__icontains=query) | User.objects.filter(useridentification__student_id__icontains=query) | User.objects.filter(username__icontains=query)

    else:
        form = UserSearchForm()
        users = User.objects.all()

    table = UserTable(users)
    return render(request, 'lookup_user.html', {'users': users, 'form': form, "table": table})

