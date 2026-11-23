// site.config MUST come first — it runs initDocs before anything renders.
import '../site.config'
import '../styles/app.css'
import '../lib/hostTheme'
export { onRenderClient } from '@dreamlake/dockit/client'
