import { useState } from "react"
import { Bell, ChevronDown, CreditCard, LogOut, Settings, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Progress } from "@/components/ui/progress"

export default function ClubDashboard() {
  const [attendanceProgress, _] = useState(75)

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Club Dashboard</h1>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon">
              <Bell className="h-5 w-5" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button  className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  <span>John Doe</span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader>
              <CardTitle>Attendance</CardTitle>
              <CardDescription>Your current attendance rate</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center">
                <Progress value={attendanceProgress} className="w-full" />
                <p className="mt-2 text-2xl font-bold">{attendanceProgress}%</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Payment Status</CardTitle>
              <CardDescription>Your membership fee status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold text-green-600">Paid</span>
                <CreditCard className="h-6 w-6 text-green-600" />
              </div>
              <p className="mt-2 text-sm text-muted-foreground">Next payment due: July 1, 2023</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Attendance Statistics</CardTitle>
              <CardDescription>Your attendance over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[120px] w-full bg-muted" />
              <p className="mt-2 text-sm text-muted-foreground">Chart placeholder: Implement actual chart here</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Account Controls</CardTitle>
              <CardDescription>Manage your account settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Button className="w-full" variant="outline">
                  <Settings className="mr-2 h-4 w-4" />
                  Account Settings
                </Button>
                <Button className="w-full" variant="outline">
                  <CreditCard className="mr-2 h-4 w-4" />
                  Billing Information
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Recent Activities</CardTitle>
            <CardDescription>Your latest club activities and events</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-4">
              {[
                { date: "2023-06-15", activity: "Attended Weekly Meeting" },
                { date: "2023-06-10", activity: "Participated in Club Workshop" },
                { date: "2023-06-05", activity: "Submitted Monthly Report" },
                { date: "2023-05-30", activity: "Attended Guest Speaker Session" },
              ].map((item, index) => (
                <li key={index} className="flex items-center justify-between border-b pb-2 last:border-b-0">
                  <span className="font-medium">{item.activity}</span>
                  <span className="text-sm text-muted-foreground">{item.date}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}