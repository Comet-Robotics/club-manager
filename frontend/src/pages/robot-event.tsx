'use client'

import { useState } from 'react'
import { Plus, Trash2, CreditCard, FileText, Check, ChevronRight } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Progress } from "@/components/ui/progress"
import { observer } from "@legendapp/state/react"


export default observer(RobotEventRegister)

type Step = {
    id: string;
    title: string;
    description: string;
    component: React.ReactNode;
  }
  
  export  function RobotEventRegister() {
    const [completedSteps, setCompletedSteps] = useState<Step[]>([])
    const [currentStepIndex, setCurrentStepIndex] = useState(0)
    const [robots, setRobots] = useState([{ name: '', weight: '' }])
    const [isPaid, setIsPaid] = useState(false)
    const [isPaperworkComplete, setIsPaperworkComplete] = useState(false)
    const [isTeam, setIsTeam] = useState<boolean | null>(null)
    const [isManager, setIsManager] = useState<boolean | null>(null)
    const [isCompeting, setIsCompeting] = useState<boolean | null>(null)
    const [isUserPaying, setIsUserPaying] = useState<boolean | null>(null)

  
    const addRobot = () => {
      setRobots([...robots, { name: '', weight: '' }])
    }
  
    const removeRobot = (index: number) => {
      setRobots(robots.filter((_, i) => i !== index))
    }
  
    const updateRobot = (index: number, field: 'name' | 'weight', value: string) => {
      const updatedRobots = [...robots]
      updatedRobots[index][field] = value
      setRobots(updatedRobots)
    }
  
    const steps: Step[] = [
    {
        id: 'is-manager',
        title: 'Are you a manager?',
        description: 'Do you manage a team of competitors?',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>Are you a manager?</CardTitle>
                <CardDescription>Do you manage a team of competitors?</CardDescription>
                </CardHeader>
                <CardContent>
                <RadioGroup onValueChange={(value) => setIsManager(value === 'yes')}>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="yes" id="yes" />
                    <Label htmlFor="yes">Yes</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="no" id="no" />
                    <Label htmlFor="no">No</Label>
                    </div>
                </RadioGroup>
                </CardContent>
            </Card>
        )
    },
    {
        id: 'select-robots',
        title: 'Choose your robots!',
        description: 'Which robots will you be competing with?',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>Choose your robots!</CardTitle>
                <CardDescription>Which robots will you be competing with?</CardDescription>
                </CardHeader>
            </Card>
        )
    },
    {
        id: 'select-team',
        title: 'Which team are you managing?',
        description: 'What is the name of the team you manage?',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>Which team are you managing?</CardTitle>
                <CardDescription>what is your team?</CardDescription>
                </CardHeader>
            </Card>
        )
    },
    {
        id: 'is-manager-competing',
        title: 'Which team are you managing?',
        description: 'What is the name of the team you manage?',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>Will you be competing?</CardTitle>
                <CardDescription>As a team manager, will you be bringing a robot?</CardDescription>
                </CardHeader>
                <CardContent>
                <RadioGroup onValueChange={(value) => setIsCompeting(value === 'yes')}>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="yes" id="yes" />
                    <Label htmlFor="yes">Yes</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="no" id="no" />
                    <Label htmlFor="no">No</Label>
                    </div>
                </RadioGroup>
                </CardContent>
            </Card>
        )
    },
    {
        id: 'is-user-paying',
        title: 'Will you be paying or is the team?',
        description: 'Will your team manager be paying for the registration?',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>Will you be paying or is the team?</CardTitle>
                <CardDescription>Will your team manager be paying for the registration?</CardDescription>
                </CardHeader>
                <CardContent>
                <RadioGroup onValueChange={(value) => setIsUserPaying(value === 'yes')}>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="yes" id="yes" />
                    <Label htmlFor="yes">I am paying</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                    <RadioGroupItem value="no" id="no" />
                    <Label htmlFor="no">Team is paying</Label>
                    </div>
                </RadioGroup>
                </CardContent>
            </Card>
        )
    },
    {
        id: 'cart-payment',
        title: 'PAY UP',
        description: 'ITS TIME TO PAY',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>ITS TIME TO PAY </CardTitle>
                <CardDescription>gimme ur money</CardDescription>
                </CardHeader>
            </Card>
        )
    },
    {
        id: 'sign-waiver',
        title: 'SIGN HERE',
        description: 'GIVE US UR SOUL',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>SIGN HERE</CardTitle>
                <CardDescription>GIVE US UR SOUL</CardDescription>
                </CardHeader>
            </Card>
        )
    },
    {
        id: 'registration-complete',
        title: 'all done <3',
        description: 'no more form',
        component: (
            <Card>
                <CardHeader>
                <CardTitle>all done!3</CardTitle>
                <CardDescription>no more form</CardDescription>
                </CardHeader>
            </Card>
        )
    },

    
      {
        id: 'create-robots',
        title: 'Create Robots',
        description: 'Add details for each robot you want to register',
        component: (
          <Card>
            <CardHeader>
              <CardTitle>Create Your Robots</CardTitle>
              <CardDescription>Add details for each robot you want to register</CardDescription>
            </CardHeader>
            <CardContent>
              {robots.map((robot, index) => (
                <div key={index} className="mb-4 space-y-2">
                  <div className="flex items-center space-x-2">
                    <Input
                      placeholder="Robot Name"
                      value={robot.name}
                      onChange={(e) => updateRobot(index, 'name', e.target.value)}
                    />
                    <Input
                      placeholder="Weight (lbs)"
                      type="number"
                      value={robot.weight}
                      onChange={(e) => updateRobot(index, 'weight', e.target.value)}
                    />
                    <Button variant="destructive" size="icon" onClick={() => removeRobot(index)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
            <CardFooter>
              <Button onClick={addRobot}>
                <Plus className="mr-2 h-4 w-4" /> Add Another Robot
              </Button>
            </CardFooter>
          </Card>
        )
      },
      {
        id: 'team-question',
        title: 'Team Registration',
        description: 'Are you registering as a team?',
        component: (
          <Card>
            <CardHeader>
              <CardTitle>Team Registration</CardTitle>
              <CardDescription>Are you registering as a team?</CardDescription>
            </CardHeader>
            <CardContent>
              <RadioGroup onValueChange={(value) => setIsTeam(value === 'yes')}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="yes" id="yes" />
                  <Label htmlFor="yes">Yes</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="no" id="no" />
                  <Label htmlFor="no">No</Label>
                </div>
              </RadioGroup>
            </CardContent>
          </Card>
        )
      },
      {
        id: 'team-details',
        title: 'Team Details',
        description: 'Provide information about your team',
        component: (
          <Card>
            <CardHeader>
              <CardTitle>Team Details</CardTitle>
              <CardDescription>Provide information about your team</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="team-name">Team Name</Label>
                  <Input id="team-name" placeholder="Enter your team name" />
                </div>
                <div>
                  <Label htmlFor="team-members">Number of Team Members</Label>
                  <Input id="team-members" type="number" placeholder="Enter number of team members" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      },
      {
        id: 'payment',
        title: 'Pay Registration',
        description: 'Complete payment to proceed with registration',
        component: (
          <Card>
            <CardHeader>
              <CardTitle>Pay Registration Fees</CardTitle>
              <CardDescription>Complete payment to proceed with registration</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4">Total due: ${robots.length * 50}</p>
              <Button onClick={() => setIsPaid(true)} disabled={isPaid}>
                <CreditCard className="mr-2 h-4 w-4" /> Pay Now
              </Button>
            </CardContent>
          </Card>
        )
      },
      {
        id: 'paperwork',
        title: 'Complete Paperwork',
        description: 'Fill out required forms for the event',
        component: (
          <Card>
            <CardHeader>
              <CardTitle>Complete Paperwork</CardTitle>
              <CardDescription>Fill out required forms for the event</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="waiver">Liability Waiver</Label>
                  <Input id="waiver" type="file" />
                </div>
                <div>
                  <Label htmlFor="rules">Rules Acknowledgment</Label>
                  <Input id="rules" type="file" />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => setIsPaperworkComplete(true)} disabled={isPaperworkComplete}>
                <FileText className="mr-2 h-4 w-4" /> Submit Paperwork
              </Button>
            </CardFooter>
          </Card>
        )
      }
    ]
  
    const getCurrentStep = () => {
      return steps[currentStepIndex]
    }
  
    const handleNext = () => {
      const currentStep = getCurrentStep()
      setCompletedSteps([...completedSteps, currentStep])
  
      if (currentStepIndex === 0 && isManager === false) {
        setIsCompeting(true)
        setCurrentStepIndex(1)
      } else if (currentStepIndex === 0 && isManager === true) {
        setCurrentStepIndex(2)
      } else if (currentStepIndex === 2) {
        setCurrentStepIndex(3)
      } else if (currentStepIndex === 3 && isCompeting === true) {
        setCurrentStepIndex(1)
      } else if (currentStepIndex === 3 && isCompeting === false) {
        setCurrentStepIndex(5)
      } else if (currentStepIndex === 1 && isManager === true) {
        setCurrentStepIndex(5)
      } else if (currentStepIndex === 1 && isManager === false) {
        setCurrentStepIndex(4)
      }else if (currentStepIndex === 4 && isUserPaying === true) {
        setCurrentStepIndex(5)
      }else if (currentStepIndex === 4 && isUserPaying === false) {
        setCurrentStepIndex(6)
      }else if (currentStepIndex === 5 && isCompeting === true) {
        setCurrentStepIndex(6)
      }else if (currentStepIndex === 1 && (isCompeting === false || isCompeting === null)) {
        setCurrentStepIndex(7)
      }
      else if (currentStepIndex === 6 ) {
        setCurrentStepIndex(7)
      }else {
        setCurrentStepIndex(currentStepIndex + 1)
      }
    }
  
    const handlePrevious = () => {
      if (currentStepIndex > 0) {
        setCompletedSteps(completedSteps.slice(0, -1))
        setCurrentStepIndex(currentStepIndex - 1)
      }
    }
  
    const isStepComplete = () => {
      switch (getCurrentStep().id) {
        case 'is-manager':
            return isManager !== null
        case 'select-robots':
            return true
        case 'select-team':
            return true
        case 'is-user-paying':
            return isUserPaying !== null
        case 'is-manager-competing':
            return isCompeting !== null
        case 'create-robots':
          return robots.length > 0 && robots.every(robot => robot.name && robot.weight)
        case 'team-question':
          return isTeam !== null
        case 'team-details':
          return true // Assume team details are always complete for simplicity
        case 'payment':
          return isPaid
        case 'paperwork':
          return isPaperworkComplete
        default:
          return true
      }
    }
  
    return (
      <div className="flex flex-col h-screen bg-background p-6">
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Robot Combat Championship 2024</CardTitle>
            <CardDescription>Complete your registration</CardDescription>
          </CardHeader>
        </Card>
  
        <div className="flex flex-1 gap-6 overflow-hidden">
          <div className="w-1/3 space-y-4 overflow-y-auto">
            {completedSteps.map((step, index) => (
              <Card key={step.id} className="border-green-500">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Check className="mr-2 h-5 w-5 text-green-500" />
                    {step.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </CardContent>
              </Card>
            ))}
            {getCurrentStep() && (
              <Card className="border-blue-500">
                <CardHeader>
                  <CardTitle>{getCurrentStep().title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{getCurrentStep().description}</p>
                </CardContent>
              </Card>
            )}
          </div>
  
          <div className="w-2/3 overflow-y-auto">
            {getCurrentStep().component}
  
            <div className="mt-6 flex justify-between">
              <Button 
                onClick={handlePrevious}
                disabled={currentStepIndex === 0}
              >
                Previous
              </Button>
              <Button 
                onClick={handleNext}
                disabled={!isStepComplete() || currentStepIndex === steps.length - 1}
              >
                {currentStepIndex === steps.length - 1 ? 'Finish' : 'Next'} <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }