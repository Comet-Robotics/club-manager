import { observable } from "@legendapp/state";
import { syncObservable } from '@legendapp/state/sync'
import { ObservablePersistLocalStorage } from "@legendapp/state/persist-plugins/local-storage"
import { User } from "./types";
import type { paths } from "./api-schema";
import createClient from "openapi-fetch";

const apiClient = createClient<paths>({ baseUrl: "/" })

type TestStore = {
  user: string
}

export const testStore$  = observable<TestStore>({
  user: "This is some sample state that gets persisted on refresh",
})

syncObservable(testStore$, {
    persist: {
        name: 'testStore',
        plugin: ObservablePersistLocalStorage
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
    if (loginRes.error) return null
    
    const whoamiRes = await apiClient.GET("/api/auth/whoami/")
    if (whoamiRes.error) return null
    
    const userRes = await apiClient.GET("/api/users/{id}/", {
      params: {
        path: {
          id: whoamiRes.data.id
        }
      }
    })
    if (userRes.error) return null
    
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
