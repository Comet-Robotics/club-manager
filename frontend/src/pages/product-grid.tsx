import { useEffect, useState } from 'react'
import { ShoppingCart, Minus, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cart$ } from '@/lib/state'
import { observer } from "@legendapp/state/react"
import { apiClient } from '@/lib/state'

export default observer(ProductGrid)

interface Product {
    id: number
    name: string
    amount_cents: number
}

export function ProductGrid() {

    const [products, setProducts] = useState([] as Product[])

    useEffect(()=>{
      apiClient.GET("/api/products/").then((res) => {
        if (res.error || !res.data) return
        setProducts(res.data)
      })
    }, [])

  const addToCart = (productId: number) => {
    cart$.quantities.set({ ...cart$.quantities.get(), [productId]: (cart$.quantities.get()[productId] || 0) + 1 })
  }

  const updateQuantity = (productId: number, delta: number) => {
    const newQuantities = { ...cart$.quantities.get() }
    if (!newQuantities[productId]) return
    newQuantities[productId] += delta
    if (newQuantities[productId] <= 0) {
      delete newQuantities[productId]
    }
    cart$.quantities.set(newQuantities)
  }

    const cartCount = Object.values(cart$.quantities.get()).reduce((acc, quantity) => acc + quantity, 0)

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-end mb-4">
        <Button variant="default" size="sm" className="relative">
          <ShoppingCart className="h-5 w-5 mr-2" />
          Cart
          {cartCount > 0 && (
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
              {cartCount}
            </span>
          )}
        </Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map(product => (
          <Card key={product.id} className="overflow-hidden">
            <img
              src={product.image}
              alt={product.name}
              className="w-full h-[300px] object-cover"
            />
            <CardContent className="p-4">
              <h2 className="text-lg font-semibold mb-2">{product.name}</h2>
              <p className="text-gray-600 mb-4">${(product.amount_cents/100).toFixed(2)}</p>
              {cart$.quantities.get()[product.id] ? (
                <div className="flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => updateQuantity(product.id, -1)}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <span className="mx-2 font-semibold">{cart$.quantities.get()[product.id]}</span>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => updateQuantity(product.id, 1)}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Button className="w-full" onClick={() => addToCart(product.id)}>
                  Add to Cart
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}