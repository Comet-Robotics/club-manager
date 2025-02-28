from django.test import TestCase

from seed import create_test_data
from projects.models import Project, Team
from django.contrib.auth.models import User

class TeamManagementTest(TestCase):
  def setUp(self):
    create_test_data()
    self.srp_project = Project.objects.get(name="Seeded:Solis Rover Project")
    self.mech_team = Team.objects.get(name="Seeded:Mechanical")
    self.arm_team = Team.objects.get(name="Seeded:Arm")
    self.wheel_team = Team.objects.get(name="Seeded:Wheel Design")
    
    self.officer = User.objects.get(username="seeded_officer")
    self.srp_pm = User.objects.get(username="seeded_srp_pm")
    self.mech_lead = User.objects.get(username="seeded_mech_lead")
    self.arm_lead = User.objects.get(username="seeded_arm_lead")
    self.wheel_lead = User.objects.get(username="seeded_wheel_lead")
    self.wheel_member = User.objects.get(username="seeded_wheel_member")

  def test_project_manager_can_manage_any_team(self):
    """Project managers should be able to manage any team in their project"""
    self.assertTrue(Team.user_can_manage_team(self.srp_pm, self.mech_team))
    self.assertTrue(Team.user_can_manage_team(self.srp_pm, self.arm_team))
    self.assertTrue(Team.user_can_manage_team(self.srp_pm, self.wheel_team))

  def test_officer_can_manage_any_team(self):
    """Officers (superusers) should be able to manage any team"""
    self.assertTrue(Team.user_can_manage_team(self.officer, self.mech_team))
    self.assertTrue(Team.user_can_manage_team(self.officer, self.arm_team))
    self.assertTrue(Team.user_can_manage_team(self.officer, self.wheel_team))

  def test_team_lead_can_manage_own_team(self):
    """Team leads should be able to manage their own team"""
    self.assertTrue(Team.user_can_manage_team(self.mech_lead, self.mech_team))
    self.assertTrue(Team.user_can_manage_team(self.arm_lead, self.arm_team))
    self.assertTrue(Team.user_can_manage_team(self.wheel_lead, self.wheel_team))

  def test_team_lead_can_manage_child_teams(self):
    """Team leads should be able to manage teams under their team"""
    self.assertTrue(Team.user_can_manage_team(self.mech_lead, self.arm_team))
    self.assertTrue(Team.user_can_manage_team(self.mech_lead, self.wheel_team))

  def test_team_lead_cannot_manage_other_teams(self):
    """Team leads should not be able to manage teams they don't lead or aren't under their team"""
    # Arm lead shouldn't be able to manage mechanical team (parent) or wheel team (different branch)
    self.assertFalse(Team.user_can_manage_team(self.arm_lead, self.mech_team))
    self.assertFalse(Team.user_can_manage_team(self.arm_lead, self.wheel_team))

  def test_regular_member_cannot_manage_teams(self):
    """Regular team members should not be able to manage any teams"""
    self.assertFalse(Team.user_can_manage_team(self.wheel_member, self.wheel_team))
    self.assertFalse(Team.user_can_manage_team(self.wheel_member, self.arm_team))
    self.assertFalse(Team.user_can_manage_team(self.wheel_member, self.mech_team))


class ProjectTest(TestCase):
  def setUp(self):
    create_test_data()

    self.not_officer = User.objects.get(username="seeded_not_officer")
    self.officer = User.objects.get(username="seeded_officer")

    self.srp_proj = Project.objects.get(name="Seeded:Solis Rover Project")

    self.srp_mech_lead = User.objects.get(username="seeded_mech_lead")
    self.mech_team = Team.objects.get(name="Seeded:Mechanical")
    
    self.arm_team = Team.objects.get(name="Seeded:Arm")
    self.wheel_team = Team.objects.get(name="Seeded:Wheel Design")

    self.chessbot_proj = Project.objects.get(name="Seeded:ChessBots")

    self.chessbot_pm = User.objects.get(username="seeded_cb_pm")
    self.chessbot_team_lead = User.objects.get(username="seeded_sw_lead")

    self.srp_pm = User.objects.get(username="seeded_srp_pm")

  def test_direct_teams(self):
    self.assertEqual(self.mech_team.direct_teams().count(), 2)

  def test_all_team_members_on_team(self):
    self.assertEqual(len(self.mech_team.all_team_members()), 5)

    self.assertEqual(len(self.wheel_team.all_team_members()), 2)

  def test_getting_project_team_members(self):
    # 5 team leads + 1 team member + 1 pm = 7 members
    self.assertEqual(self.srp_proj.all_team_members().count(), 7)
    
    # 2 team leads + 1 pm = 3 members
    self.assertEqual(self.chessbot_proj.all_team_members().count(), 3)

  def test_getting_project_teams(self):
    self.assertEqual(self.srp_proj.all_teams().count(), 5)
    
    self.assertEqual(self.chessbot_proj.all_teams().count(), 2)

  def test_getting_project_direct_teams(self):
    self.assertEqual(self.srp_proj.direct_teams().count(), 2)
    
    self.assertEqual(self.chessbot_proj.direct_teams().count(), 1)

  def test_officers_can_manage_project(self):
    self.assertTrue(Project.user_can_manage_project(self.officer, self.srp_proj))

    
    self.assertFalse(Project.user_can_manage_project(self.not_officer, self.srp_proj))

  def test_project_managers_can_manage_project(self):
    self.assertTrue(Project.user_can_manage_project(self.srp_pm, self.srp_proj))

    
    self.assertFalse(Project.user_can_manage_project(self.srp_mech_lead, self.srp_proj))


    self.assertFalse(Project.user_can_manage_project(self.chessbot_pm, self.srp_proj))

    self.assertFalse(Project.user_can_manage_project(self.chessbot_team_lead, self.srp_proj))


