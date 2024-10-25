import { createLazyFileRoute } from '@tanstack/react-router'
import  ProductGrid from '@/pages/product-grid.tsx'
import { observer } from "@legendapp/state/react"


export const Route = createLazyFileRoute('/store')({
  component: () => <ProductGrid/>,
})

