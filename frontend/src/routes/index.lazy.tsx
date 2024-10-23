import UserDashboard from '@/pages/user-dashboard'
import Checkout from '@/pages/checkout'
import { createLazyFileRoute } from '@tanstack/react-router'
import { Check } from 'lucide-react'

export const Route = createLazyFileRoute('/')({
  component: Index,
})

function Index() {
  return (
    <Checkout />
  )
}