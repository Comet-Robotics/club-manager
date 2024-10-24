import { observable } from "@legendapp/state";
import { syncObservable } from '@legendapp/state/sync'
import { ObservablePersistLocalStorage } from "@legendapp/state/persist-plugins/local-storage"

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
