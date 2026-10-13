import { useEffect, useState } from 'react'
import { Header } from './Header'
import { PipelineStepper } from './PipelineStepper'
import { HealthBar } from './HealthBar'
import { HierarchyTree } from './HierarchyTree'
import { NodeInspector } from './NodeInspector'
import { ChatThread } from './ChatThread'
import { ChatComposer } from './ChatComposer'
import { PeerChatOverlay } from './PeerChatOverlay'
import { ProcessTimeline } from './ProcessTimeline'

export function Layout() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="app">
      <Header className={mounted ? 'animate-slide-down' : ''} />
      <div className="app-body">
        <aside className={`sidebar ${mounted ? 'animate-slide-in-right stagger-1' : ''}`} style={{ animationDelay: mounted ? '0ms' : '0ms' }}>
          <PipelineStepper />
          <HealthBar />
          <HierarchyTree />
        </aside>

        <main className={`chat-main ${mounted ? 'animate-fade-in stagger-2' : ''}`} style={{ animationDelay: mounted ? '80ms' : '0ms' }}>
          <ProcessTimeline />
          <ChatThread />
          <ChatComposer />
        </main>

        <aside className={`inspector ${mounted ? 'animate-slide-in-right stagger-3' : ''}`} style={{ animationDelay: mounted ? '160ms' : '0ms' }}>
          <NodeInspector />
        </aside>
      </div>
      <PeerChatOverlay />
    </div>
  )
}
