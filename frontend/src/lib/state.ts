import { observable } from "@legendapp/state";
import { syncObservable } from '@legendapp/state/sync'
import { ObservablePersistLocalStorage } from "@legendapp/state/persist-plugins/local-storage"
import { User } from "./types";
import type { paths } from "./api-schema";
import createClient from "openapi-fetch";
import { syncedCrud } from '@legendapp/state/sync-plugins/crud'

export const apiClient = createClient<paths>({ baseUrl: "/" })

type CartStore = {
  quantities: { [key: number]: number }
}

export const products$ = observable(syncedCrud({
  list: async () => {
    const res = await apiClient.GET("/api/products/")
    if (res.error || !res.data) return []
    return res.data
  }
}))


export const cart$ = observable<CartStore>({
  quantities: {},
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
