import { createLazyFileRoute } from '@tanstack/react-router'
import { RobotEventRegister } from '@/pages/RobotEvent'

export const Route = createLazyFileRoute('/combat-events/$eventId')({
  component: () => <RobotEventRegister />,
})
