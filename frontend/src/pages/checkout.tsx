import { useMemo, useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { PaymentForm, CreditCard, ApplePay,
    GooglePay } from 'react-square-web-payments-sdk';
import { cart$, products$ } from '@/lib/state'
import { observer } from "@legendapp/state/react"
import { Link } from '@tanstack/react-router'

export default observer(Component)

function Component() {
  
  
  const subtotal = cart$.subTotal.get()
  const total = subtotal


  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Checkout</h1>
      <Link to="/store" className="text-blue-500 hover:underline">Back to store</Link>
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="w-full lg:w-2/3">
          <Card>
            <CardHeader>
              <CardTitle>Your Cart</CardTitle>
              <CardDescription>Review your items before checkout</CardDescription>
            </CardHeader>
            <CardContent>
              {cart$.cartItems.map((item$) => {
                const item = item$.get()
                return (
                <div key={item.id} className="flex items-center justify-between py-4">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-gray-200 rounded-md">
                      {item.image && <img
                        src={item.image}
                        alt={item.name}
                        className="w-full h-full object-cover"
                      />}
                    </div>
                    <div>
                      <h3 className="font-semibold">{item.name}</h3>
                      <p className="text-sm text-gray-500">${(item.amount_cents/100).toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => cart$.updateQuantity(item.id, Math.max(0, item.quantity - 1))}
                    >
                      -
                    </Button>
                    <span>{item.quantity}</span>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => cart$.updateQuantity(item.id, item.quantity + 1)}
                    >
                      +
                    </Button>
                  </div>
                </div>
              )})}
            </CardContent>
            <Separator className="my-4" />
            <CardFooter className="flex flex-col items-end">
              <div className="text-sm text-gray-500">Subtotal: ${subtotal.toFixed(2)}</div>
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