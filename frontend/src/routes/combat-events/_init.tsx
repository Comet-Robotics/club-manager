import { combatEvent$, events$ } from '@/lib/state'
import { when } from '@legendapp/state'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/combat-events/_init')({
  loader: async () => {
    await Promise.all([when(combatEvent$), when(events$)])
  },
})
