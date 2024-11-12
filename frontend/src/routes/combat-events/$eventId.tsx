import { createFileRoute, notFound } from '@tanstack/react-router'
import { RobotEventRegister } from '@/pages/RobotEvent'
import { apiClient, combatEvent$, events$ } from '@/lib/state'
import { when } from '@legendapp/state'

export const Route = createFileRoute('/combat-events/$eventId')({
  component: () => {
    const {eventId, combatEventId, robotsInEvent} = Route.useLoaderData()
    return (<RobotEventRegister eventId={eventId} combatEventId={combatEventId} robotsInEvent={robotsInEvent} />)
  },
  loader: async (ctx) => {
    const combatEventId = Number(ctx.params.eventId)
      const [, , , robotsInEvent] = await Promise.all([
      when(combatEvent$),
      when(events$),
      apiClient.GET(`/api/combatevents/{combatevent_id}/robots/`, {
        params: {
          path: {
            combatevent_id: combatEventId
          }
        }
      })
    ])
    
    const combatEvent = combatEvent$.get()[combatEventId]
    if (!combatEvent) {
      throw notFound()
    }
    
    if (robotsInEvent.error || !robotsInEvent.data) {
      throw notFound()
    }
    
    const eventId = combatEvent.event_id
    return { combatEventId, eventId, robotsInEvent: robotsInEvent.data }
  },
  pendingComponent: () => <div>Loading...</div>,
})
