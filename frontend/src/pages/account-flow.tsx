'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { observer } from "@legendapp/state/react"
import { authStore$ } from '@/lib/state'

export default observer(AccountFlow)

export function AccountFlow() {
  const [view, setView] = useState<'login' | 'create'>('login')
  const [accountStep, setAccountStep] = useState(0)

  const user$ = authStore$.user.get()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")


  return (
    <>
    <div>
      <p>User: {user$ ? JSON.stringify(user$) : "no user"}</p>
    </div>
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Card className="w-[400px]">
        <CardHeader>
          <CardTitle>{view === 'login' ? 'Login' : 'Create Account'}</CardTitle>
          <CardDescription>
            {view === 'login' ? 'Enter your credentials to login' : 'Fill in your details to create an account'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {view === 'login' ? (
            <form onSubmit={(e) => {
              e.preventDefault()
              authStore$.login(username, password)}} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" placeholder="mason.thomas" required  onChange={(e) => setUsername(e.target.value)}/>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" required onChange={(e) => setPassword(e.target.value)}/>
              </div>
              <Button type="submit" className="w-full">Login</Button>
            </form>
          ) : (
            <Tabs value={accountStep.toString()} onValueChange={(value) => setAccountStep(parseInt(value))}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="0">Login Info</TabsTrigger>
                <TabsTrigger value="1">Personal Info</TabsTrigger>
              </TabsList>
              <TabsContent value="0">
                <form className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="newEmail">Email</Label>
                    <Input id="newEmail" type="email" placeholder="m@example.com" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="newPassword">Password</Label>
                    <Input id="newPassword" type="password" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <Input id="confirmPassword" type="password" required />
                  </div>
                  <Button onClick={() => setAccountStep(1)} className="w-full">Next</Button>
                </form>
              </TabsContent>
              <TabsContent value="1">
                <form onSubmit={handleCreateAccount} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input id="firstName" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input id="lastName" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input id="phone" type="tel" />
                  </div>
                  <Button type="submit" className="w-full">Create Account</Button>
                </form>
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
        <CardFooter>
          {view === 'login' ? (
            <Button variant="link" onClick={() => setView('create')} className="w-full">
              Create an account
            </Button>
          ) : (
            <Button variant="link" onClick={() => setView('login')} className="w-full">
              Back to login
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
    </>
  )
}