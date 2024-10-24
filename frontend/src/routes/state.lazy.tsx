import { createLazyFileRoute } from '@tanstack/react-router'
import { observer } from "@legendapp/state/react"
import { testStore$ } from '@/lib/state'

export const Route = createLazyFileRoute('/state')({
  component: () => <App />,
})

const App = observer(function App() {
  const user$ = testStore$.user.get()

  return (
    <>
      <p className='font-bold'>Simple example of using legend state</p>
      <input type="text" value={user$} onChange={(e) => testStore$.user.set(e.target.value)} />
    </>
  )
})