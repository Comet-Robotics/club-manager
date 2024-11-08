import { observable, syncState } from "@legendapp/state";
import { syncObservable } from '@legendapp/state/sync'
import { ObservablePersistLocalStorage } from "@legendapp/state/persist-plugins/local-storage"
import type { Product, User } from "./types";
import type { paths } from "./api-schema";
import createClient from "openapi-fetch";
import { syncedCrud } from '@legendapp/state/sync-plugins/crud'

export const apiClient = createClient<paths>({ baseUrl: "/" })

export const products$ = observable(syncedCrud({
  list: async () => {
    const res = await apiClient.GET("/api/products/")
    if (res.error || !res.data) return []
    return res.data
  }
}))

export const productMeta$ = syncState(products$) 


export const cart$ = observable({
  quantities: {} as { [key: string]: number },
  cartCount: () => Object.values(cart$.quantities.get()).reduce((acc, quantity) => acc + quantity, 0),
  subTotal: () => Object.values(cart$.cartItems.get()).reduce((acc, product) => {
    return acc + product.quantity * product.amount_cents/100
  }, 0),
  addToCart: (productId: number) => {
    cart$.quantities.assign({ [productId]: 1 })
  },
  updateQuantity: (productId: number, delta: number) => {
    
    const prev = cart$.quantities[productId]?.get()
    if (!prev) return
    const newState = prev + delta

    if (newState <= 0) {
      cart$.quantities[productId]?.delete()
    } else {
      cart$.quantities.assign({ [productId]: newState })
    }

  },
  cartItems: () => {
    return Object.entries(cart$.quantities.get()).reduce((acc, [productId, quantity]) => {
      const item = products$.get()[productId as unknown as number]
      if (!item) return acc
      return [...acc, {...item, quantity}]
    }, [] as (Product & {quantity: number})[])
  }

})

type AuthStore = {
  user: User | null
  login: (username: string, password: string) => Promise<User | null>
}

export const authStore$ = observable<AuthStore>({
  user: null,
  login: async (username: string, password: string) => {
    const loginRes = await apiClient.POST("/api/auth/login/", {
      body: {
        username: username,
        password: password
      }
    })
    if (loginRes.error || !loginRes.data) return null
    
    const whoamiRes = await apiClient.GET("/api/auth/whoami/")
    if (whoamiRes.error || !whoamiRes.data) return null
    
    const userRes = await apiClient.GET("/api/users/{id}/", {
      params: {
        path: {
          id: whoamiRes.data.id
        }
      }
    })
    if (userRes.error || !userRes.data) return null
    
    const user = userRes.data
    authStore$.user.set(user)
    return user
  }
})

syncObservable(authStore$, {
  persist: {
    name: 'authStore',
    plugin: ObservablePersistLocalStorage
  }
})
