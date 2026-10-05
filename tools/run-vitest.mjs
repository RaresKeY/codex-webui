// Deno's worker-thread teardown is incomplete. A custom Vitest 4 fork pool
// keeps the worker launch explicit, instead of Deno's default `run -A` fork.
import { fork } from 'node:child_process'
import { ForksPoolWorker, startVitest } from '../frontend/node_modules/vitest/dist/node.js'

class ScopedForks extends ForksPoolWorker {
  name = 'deno-scoped-forks'

  async start() {
    this._fork ||= fork(this.entrypoint, [], {
      env: this.env,
      execArgv: this.execArgv,
      execPath: '/app/tools/deno-worker.py',
      stdio: 'pipe',
      serialization: 'advanced',
    })
    for (const stream of ['stdout', 'stderr']) {
      if (this._fork[stream]) {
        this[stream].setMaxListeners(1 + this[stream].getMaxListeners())
        this._fork[stream].pipe(this[stream])
      }
    }
  }
}

const context = await startVitest('test', [], {
  run: true,
  maxWorkers: 2,
  pool: { name: 'deno-scoped-forks', createPoolWorker: options => new ScopedForks(options) },
})
await context?.close()
