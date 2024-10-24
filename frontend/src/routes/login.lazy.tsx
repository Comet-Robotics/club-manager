import { createLazyFileRoute } from '@tanstack/react-router'
import { observer } from '@legendapp/state/react'
import { authStore$ } from '@/lib/state'
import { useState } from 'react'

export const Route = createLazyFileRoute('/login')({
  component: () => <App />,
})

const App = observer(function App() {
  const user$ = authStore$.user.get()

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  return (
    <>
      <p>User: {user$ ? JSON.stringify(user$) : "no user"}</p>
      <p className="font-bold">Login</p>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button
        onClick={() => authStore$.login(username, password)}
      >login lol</button>
    </>
  )
})
