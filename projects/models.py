from django.db import models
from django.utils.translation import gettext_lazy as _

"""
The goal of this app is to allow a project manager to easily view retention from meeting to meeting on their project, as well as being able to programmatically grant members access to project resources like GitHub repositories based on team membership. To do this, we need to be able to mark a user as being a 'member' to a project and/or subteam(s) within that project.

Projects are the top level organizational unit. A project can have multiple subteams. Each subteam can have multiple team members. A user can be a member of multiple subteams. This allows us to create a tree-like structure, like the one below.

Project: Solis Rover Project
  - Subteam: Mechanical
    - Team Member: John Doe
    - Team Member: Jane Doe
    - Subteam: Arm
      - Team Member: John Doe
      - Team Member: Megan Doe
  - Subteam: Embedded
    - Team Member: Emily Doe
    - Team Member: Michael Doe
"""

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    default_subteam = models.ForeignKey('SubTeam', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
        
    def all_team_members(self):
      return TeamMember.objects.filter(subteam__project=self)
      
    def direct_subteams(self):
      return Subteam.objects.filter(project=self)

class Subteam(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    parent_subteam = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
      if self.parent_subteam:
        return self.parent_subteam.name + " > " + self.name
      else:
        return self.project.name + " | " + self.name

    def direct_team_members(self):
      return TeamMember.objects.filter(subteam=self)
      
    def direct_subteams(self):
      return Subteam.objects.filter(parent_subteam=self)
      
    def all_subteams(self):
      subteams = self.direct_subteams()
      for subteam in subteams:
        subteams.extend(subteam.all_subteams())
      return subteams
      
    def all_team_members(self):
      members = self.direct_team_members()
      for subteam in self.all_subteams():
        members.extend(subteam.all_members())
      return members

class TeamMember(models.Model):
    class Role(models.TextChoices):
      LEAD = "LEAD", _("Team Lead")
      MEMBER = "MEMBER", _("Team Member")
  
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    subteam = models.ForeignKey(Subteam, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(choices=Role.choices, default=Role.MEMBER)
    
    class Meta:
      constraints = [
          models.UniqueConstraint(fields=['user', 'subteam'], name='unique_user_subteam')
      ]

    def __str__(self):
        return f"{self.role}: {str(self.user)} - {str(self.subteam)}"        
