import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { PaymentForm, CreditCard, ApplePay,
    GooglePay } from 'react-square-web-payments-sdk';


export default function Component() {
  const [cartItems, setCartItems] = useState([
    { id: 1, name: "Product 1", price: 19.99, quantity: 2 },
    { id: 2, name: "Product 2", price: 29.99, quantity: 1 },
    { id: 3, name: "Product 3", price: 39.99, quantity: 3 },
  ])

  const subtotal = cartItems.reduce((acc, item) => acc + item.price * item.quantity, 0)
  const tax = subtotal * 0.1 // Assuming 10% tax
  const total = subtotal + tax

  const updateQuantity = (id: number, newQuantity: number) => {
    setCartItems(cartItems.map(item => 
      item.id === id ? { ...item, quantity: newQuantity } : item
    ))
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Checkout</h1>
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="w-full lg:w-2/3">
          <Card>
            <CardHeader>
              <CardTitle>Your Cart</CardTitle>
              <CardDescription>Review your items before checkout</CardDescription>
            </CardHeader>
            <CardContent>
              {cartItems.map((item) => (
                <div key={item.id} className="flex items-center justify-between py-4">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-gray-200 rounded-md"></div>
                    <div>
                      <h3 className="font-semibold">{item.name}</h3>
                      <p className="text-sm text-gray-500">${item.price.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => updateQuantity(item.id, Math.max(0, item.quantity - 1))}
                    >
                      -
                    </Button>
                    <span>{item.quantity}</span>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => updateQuantity(item.id, item.quantity + 1)}
                    >
                      +
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
            <Separator className="my-4" />
            <CardFooter className="flex flex-col items-end">
              <div className="text-sm text-gray-500">Subtotal: ${subtotal.toFixed(2)}</div>
              <div className="text-sm text-gray-500">Tax: ${tax.toFixed(2)}</div>
              <div className="text-lg font-semibold">Total: ${total.toFixed(2)}</div>
            </CardFooter>
          </Card>
        </div>
        <div className="w-full lg:w-1/3">
          <Card>
            <CardHeader>
              <CardTitle>Payment Details</CardTitle>
              <CardDescription>Enter your payment information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
            <PaymentForm
        applicationId="sandbox-sq0idb-2FWA0_G2AlLk3IrjzXvNfg"
        cardTokenizeResponseReceived={(token, verifiedBuyer) => {
          console.log('token:', token);
          console.log('verifiedBuyer:', verifiedBuyer);
        }}
        createPaymentRequest={() => ({
            countryCode: "US",
            currencyCode: "USD",
            total: {
              amount: "1.00",
              label: "Total",
            },
          })}
        locationId='L0Z6ER7EWTR67'
      >
          <CreditCard />
          <ApplePay />
          <GooglePay />
      </PaymentForm>
            </CardContent>
            <CardFooter>
              <Button className="w-full">Pay ${total.toFixed(2)}</Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  )
}