import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
from clubManager import settings
import django

django.setup()


from django.contrib.auth.models import User
from projects.models import Project, Team


PASSWORD = "j"
SEEDED_OBJECT_NAME_PREFIX = "Seeded:"


def create_officer():
    officer = User.objects.create_user(
        username="seeded_officer",
        password=PASSWORD,
        is_staff=True,
        is_superuser=True,
    )

    not_officer = User.objects.create_user(username="seeded_not_officer", password=PASSWORD)


def create_srp_project():
    proj = Project.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Solis Rover Project",
        description="Seeded project",
    )

    mech_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Mechanical",
        description="Seeded team",
        project=proj,
    )
    arm_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Arm",
        description="Seeded team",
        parent_team=mech_team,
        project=proj,
    )
    dt_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Drivetrain",
        description="Seeded team",
        parent_team=mech_team,
        project=proj,
    )
    wheel_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Wheel Design",
        description="Seeded team",
        parent_team=dt_team,
        project=proj,
    )

    embed_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Embedded",
        description="Seeded team",
        project=proj,
    )

    srp_pm = User.objects.create_user(username="seeded_srp_pm", password=PASSWORD)
    proj.managers.add(srp_pm)
    proj.save()

    mech_lead = User.objects.create_user(username="seeded_mech_lead", password=PASSWORD)
    mech_team.leads.add(mech_lead)

    arm_lead = User.objects.create_user(username="seeded_arm_lead", password=PASSWORD)
    arm_team.leads.add(arm_lead)

    dt_lead = User.objects.create_user(username="seeded_dt_lead", password=PASSWORD)
    dt_team.leads.add(dt_lead)

    wheel_lead = User.objects.create_user(username="seeded_wheel_lead", password=PASSWORD)
    wheel_team.leads.add(wheel_lead)

    wheel_member = User.objects.create_user(username="seeded_wheel_member", password=PASSWORD)
    wheel_team.members.add(wheel_member)

    embed_lead = User.objects.create_user(username="seeded_embed_lead", password=PASSWORD)
    embed_team.leads.add(embed_lead)

    print("Seeded!")


def create_chessbot_project():
    proj = Project.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "ChessBots",
        description="Seeded project",
    )

    sw_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Software",
        description="Seeded team",
        project=proj,
    )
    hw_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Hardware",
        description="Seeded team",
        parent_team=sw_team,
        project=proj,
    )

    cb_pm = User.objects.create_user(username="seeded_cb_pm", password=PASSWORD)
    proj.managers.add(cb_pm)
    proj.save()

    sw_lead = User.objects.create_user(username="seeded_sw_lead", password=PASSWORD)
    sw_team.leads.add(sw_lead)

    hw_lead = User.objects.create_user(username="seeded_hw_lead", password=PASSWORD)
    hw_team.leads.add(hw_lead)

    print("Seeded!")


def create_test_data():
    create_officer()
    create_srp_project()
    create_chessbot_project()
