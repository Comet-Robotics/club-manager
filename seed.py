from clubManager import settings


from django.contrib.auth.models import User
from projects.models import Project, Team
from django.db import transaction
from core.models import ServerSettings
from payments.models import Product, PurchasedProduct, Term, Payment
from django.utils import timezone
from datetime import timedelta


PASSWORD = "j"
SEEDED_OBJECT_NAME_PREFIX = "Seeded:"
MEMBERSHIP_PRODUCT = None


def clear_seeded_data():
    """Deletes all objects created by the seed script."""
    User.objects.filter(username__startswith="seeded_").delete()
    Project.objects.filter(name__startswith=SEEDED_OBJECT_NAME_PREFIX).delete()
    Team.objects.filter(name__startswith=SEEDED_OBJECT_NAME_PREFIX).delete()
    Product.objects.filter(name__startswith=SEEDED_OBJECT_NAME_PREFIX).delete()
    Term.objects.filter(name__startswith=SEEDED_OBJECT_NAME_PREFIX).delete()
    print("Cleared old seeded data.")


def _create_user_and_make_member(username, password, **kwargs):
    user = User.objects.create_user(username=username, password=password, **kwargs)
    if MEMBERSHIP_PRODUCT:
        with transaction.atomic():
            payment = Payment.objects.create(
                user=user, amount_cents=MEMBERSHIP_PRODUCT.amount_cents, completed_at=timezone.now()
            )
            PurchasedProduct.objects.get_or_create(product=MEMBERSHIP_PRODUCT, payment=payment)
    else:
        # This should not happen if create_test_data is set up correctly
        print(f"Warning: MEMBERSHIP_PRODUCT not set. Could not make {username} a member.")
    return user


def create_officer():
    officer = _create_user_and_make_member(
        username="seeded_officer", password=PASSWORD, is_staff=True, is_superuser=True
    )

    not_officer = _create_user_and_make_member(username="seeded_not_officer", password=PASSWORD)


def create_srp_project():
    proj = Project.objects.create(name=SEEDED_OBJECT_NAME_PREFIX + "Solis Rover Project", description="Seeded project")

    mech_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Mechanical", description="Seeded team", project=proj
    )
    arm_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Arm", description="Seeded team", parent_team=mech_team, project=proj
    )
    dt_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Drivetrain", description="Seeded team", parent_team=mech_team, project=proj
    )
    wheel_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Wheel Design", description="Seeded team", parent_team=dt_team, project=proj
    )

    embed_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Embedded", description="Seeded team", project=proj
    )

    srp_pm = _create_user_and_make_member(username="seeded_srp_pm", password=PASSWORD)
    proj.managers.add(srp_pm)
    proj.save()

    mech_lead = _create_user_and_make_member(username="seeded_mech_lead", password=PASSWORD)
    mech_team.leads.add(mech_lead)

    arm_lead = _create_user_and_make_member(username="seeded_arm_lead", password=PASSWORD)
    arm_team.leads.add(arm_lead)

    dt_lead = _create_user_and_make_member(username="seeded_dt_lead", password=PASSWORD)
    dt_team.leads.add(dt_lead)

    wheel_lead = _create_user_and_make_member(username="seeded_wheel_lead", password=PASSWORD)
    wheel_team.leads.add(wheel_lead)

    wheel_member = _create_user_and_make_member(username="seeded_wheel_member", password=PASSWORD)
    wheel_team.members.add(wheel_member)

    embed_lead = _create_user_and_make_member(username="seeded_embed_lead", password=PASSWORD)
    embed_team.leads.add(embed_lead)

    print("Seeded!")


def create_chessbot_project():
    proj = Project.objects.create(name=SEEDED_OBJECT_NAME_PREFIX + "ChessBots", description="Seeded project")

    sw_team = Team.objects.create(name=SEEDED_OBJECT_NAME_PREFIX + "Software", description="Seeded team", project=proj)
    hw_team = Team.objects.create(
        name=SEEDED_OBJECT_NAME_PREFIX + "Hardware", description="Seeded team", parent_team=sw_team, project=proj
    )

    cb_pm = _create_user_and_make_member(username="seeded_cb_pm", password=PASSWORD)
    proj.managers.add(cb_pm)
    proj.save()

    sw_lead = _create_user_and_make_member(username="seeded_sw_lead", password=PASSWORD)
    sw_team.leads.add(sw_lead)

    hw_lead = _create_user_and_make_member(username="seeded_hw_lead", password=PASSWORD)
    hw_team.leads.add(hw_lead)

    print("Seeded!")


def get_or_create_latest_term():
    latest_term = Term.objects.order_by("-start_date").first()
    if latest_term:
        return latest_term

    with transaction.atomic():
        product, _ = Product.objects.get_or_create(
            name=SEEDED_OBJECT_NAME_PREFIX + "1 Year Membership for Latest Term",
            defaults={"amount_cents": 2000, "description": "Seeded membership product", "max_purchases_per_user": 1},
        )

        return Term.objects.create(
            name=SEEDED_OBJECT_NAME_PREFIX + "Latest Term",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=365),
            product=product,
        )


def create_test_data():
    clear_seeded_data()

    current_term = get_or_create_latest_term()
    global MEMBERSHIP_PRODUCT
    MEMBERSHIP_PRODUCT = current_term.product

    create_officer()
    create_srp_project()
    create_chessbot_project()
