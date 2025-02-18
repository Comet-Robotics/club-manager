import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')
from clubManager import settings
import django
django.setup()


from django.contrib.auth.models import User
from projects.models import Project, Team


PASSWORD = 'j'
SEEDED_OBJECT_NAME_PREFIX = 'Seeded:'


def create_test_data():
  proj = Project.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Solis Rover Project", description='Seeded project')

  mech_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Mechanical", description='Seeded team', project=proj)
  arm_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Arm", description='Seeded team', parent_team=mech_team, project=proj)
  dt_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Drivetrain", description='Seeded team', parent_team=mech_team, project=proj)
  wheel_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Wheel Design", description='Seeded team', parent_team=mech_team, project=proj)
  
  embed_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX+"Embedded", description='Seeded team', project=proj)

  srp_pm = User.objects.create_user(username='seeded_srp_pm', password=PASSWORD)
  proj.managers.add(srp_pm)
  proj.save()

  mech_lead = User.objects.create_user(username='seeded_mech_lead', password=PASSWORD)
  mech_team.leads.add(mech_lead)

  arm_lead = User.objects.create_user(username='seeded_arm_lead', password=PASSWORD)
  arm_team.leads.add(arm_lead)

  dt_lead = User.objects.create_user(username='seeded_dt_lead', password=PASSWORD)
  dt_team.leads.add(dt_lead)

  wheel_lead = User.objects.create_user(username='seeded_wheel_lead', password=PASSWORD)
  wheel_team.leads.add(wheel_lead)

  embed_lead = User.objects.create_user(username='seeded_embed_lead', password=PASSWORD)
  embed_team.leads.add(embed_lead)

  print("Seeded!")

# create_test_data()
