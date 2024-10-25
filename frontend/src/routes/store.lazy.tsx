import { createLazyFileRoute } from '@tanstack/react-router'
import ProductGrid from '@/pages/product-grid.tsx'

export const Route = createLazyFileRoute('/store')({
  component: () => <ProductGrid />,
})
