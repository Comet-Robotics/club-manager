import { createLazyFileRoute } from '@tanstack/react-router'
import AccountFlow from '@/pages/account-flow.tsx'

export const Route = createLazyFileRoute('/auth')({
  component: () => <AccountFlow />,
})
