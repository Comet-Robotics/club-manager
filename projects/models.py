from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

"""
The goal of this app is to allow a project manager to easily view retention from meeting to meeting on their project, as well as being able to programmatically grant members access to project resources like GitHub repositories based on team membership. To do this, we need to be able to mark a user as being a 'member' to a project and/or team(s) within that project.

Projects are the top level organizational unit. A project can have multiple teams. Users are a member of a project through their membership of a team - projects have no direct associations with team members. Certain users can be marked as 'managers' of a team. Each team can have multiple team members. A user can be a member of multiple teams. This allows us to create a tree-like structure, like the one below.

Project: Solis Rover Project -
  - Managers: Dylan Doe, Gabriel Doe
  - Team: Mechanical
    - Team Member: John Doe
    - Team Member: Jane Doe
    - Team: Arm
      - Team Member: John Doe
      - Team Member: Megan Doe
  - Team: Embedded
    - Team Member: Emily Doe
    - Team Member: Michael Doe
"""

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    managers = models.ManyToManyField(User, related_name='projects_managing')

    def __str__(self):
        return self.name
        
    def all_team_members(self):
      # TODO: test
      return User.objects.filter(teams_in=self.all_teams())
      
    def all_teams(self):
      return Team.objects.filter(project=self)
    
    def direct_teams(self):
      return Team.objects.filter(project=self, parent_team=None)
      
    @staticmethod
    def user_can_manage_project(user: User, project: "Project"):
      # Users can manage projects they are a manager of, or if they are a superuser (only club officers should be superusers)
      return user.is_superuser or user in project.managers.all()

class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    parent_team = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    members = models.ManyToManyField(User, related_name='teams_in')
    leads = models.ManyToManyField(User, related_name='teams_leading')

    def __str__(self):
      if self.parent_team:
        return str(self.parent_team) + " > " + self.name
      else:
        return self.project.name + " | " + self.name
      
    def direct_teams(self):
      return Team.objects.filter(parent_team=self)
      
    def all_team_members(self):
      members = list(self.members)
      for team in self.direct_teams():
        members.extend(list(team.all_team_members()))
      return members

      
    @staticmethod
    def user_can_manage_team(user: User, team: "Team"):
      """
      Users can manage teams if any one of the following conditions is true:
      - they are able to manage the project that the team is in
      - if they are a lead on that specific team
      - if they are a lead on any of this team's parent teams
      """
      if Project.user_can_manage_project(user, team.project):
        return True
      
      team_to_check = team
      while team_to_check:
        # TODO: test this
        is_lead = Team.objects.filter(leads=user).exists()
        if is_lead:
          return True
        else:
          team_to_check = team_to_check.parent_team
        
      return False

