import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')
from clubManager import settings
import django
django.setup()


from django.contrib.auth.models import User
from projects.models import Project, Team, TeamMember


PASSWORD = 'j'
SEEDED_OBJECT_NAME_PREFIX = 'Seeded:'
  

def create_test_data():
  proj = Project.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Solis Rover Project", description='Seeded project')
  
  mech_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Mechanical", description='Seeded team', project=proj)
  arm_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Arm", description='Seeded team', parent_team=mech_team, project=proj)
  dt_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Drivetrain", description='Seeded team', parent_team=mech_team, project=proj)
  
  embed_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Embedded", description='Seeded team', project=proj)
  
  srp_pm = User.objects.create_user(username='srp_pm', password=PASSWORD)
  proj.managers.add(srp_pm)
  proj.save()
  
  mech_lead = User.objects.create_user(username='mech_lead', password=PASSWORD)
  TeamMember.objects.create(user=mech_lead, team=mech_team, role=TeamMember.Role.LEAD)
  
  arm_lead = User.objects.create_user(username='arm_lead', password=PASSWORD)
  TeamMember.objects.create(user=arm_lead, team=arm_team, role=TeamMember.Role.LEAD)
  
  dt_lead = User.objects.create_user(username='dt_lead', password=PASSWORD)
  TeamMember.objects.create(user=dt_lead, team=dt_team, role=TeamMember.Role.LEAD)
  
  embed_lead = User.objects.create_user(username='embed_lead', password=PASSWORD)
  TeamMember.objects.create(user=embed_lead, team=embed_team, role=TeamMember.Role.LEAD)
  
  print("Seeded!")

# create_test_data()
  
  