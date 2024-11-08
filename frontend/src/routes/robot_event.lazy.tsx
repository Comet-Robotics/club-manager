import { createLazyFileRoute } from '@tanstack/react-router'
import { RobotEventRegister } from '@/pages/robot-event'

export const Route = createLazyFileRoute('/robot_event')({
  component: () => <RobotEventRegister />,
})
