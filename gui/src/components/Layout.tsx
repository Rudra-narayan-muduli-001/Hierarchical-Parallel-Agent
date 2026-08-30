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
  return (
    <div className="app">
      <Header />
      <div className="app-body">
        <aside className="sidebar">
          <PipelineStepper />
          <HealthBar />
          <HierarchyTree />
        </aside>

        <main className="chat-main">
          <ProcessTimeline />
          <ChatThread />
          <ChatComposer />
        </main>

        <aside className="inspector">
          <NodeInspector />
        </aside>
      </div>
      <PeerChatOverlay />
    </div>
  )
}
