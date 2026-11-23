/**
 * Follow the theme of a DreamLake host frame when the site runs as a static-site
 * artifact (`dl artifact push --site`).
 *
 * The isolated site origin does not inherit the host's CSS. The frame protocol
 * (dreamlake-ai/frame/main.ts) is: the site posts
 * `{source: 'dreamlake-artifact-child', type: 'ready', route}` to its parent;
 * the frame answers `{source: 'dreamlake-artifact-child-host', type: 'theme', theme}`
 * now and on every host theme change. While hosted, the host theme wins over
 * dockit's own ThemeProvider and the topbar theme toggle is hidden. Outside a
 * frame this module does nothing.
 */

type HostMessage = { source?: string; type?: string; theme?: string }

function start(): void {
  if (typeof window === 'undefined' || window.parent === window) return
  const root = document.documentElement
  let hostTheme: 'light' | 'dark' | null = null

  const apply = () => {
    if (hostTheme && root.getAttribute('data-theme') !== hostTheme) root.setAttribute('data-theme', hostTheme)
  }
  // dockit's ThemeProvider stamps data-theme from its own state; keep the host's.
  new MutationObserver(apply).observe(root, { attributes: true, attributeFilter: ['data-theme'] })

  window.addEventListener('message', (event: MessageEvent<HostMessage>) => {
    if (event.source !== window.parent) return
    const data = event.data
    if (data?.source !== 'dreamlake-artifact-child-host' || data.type !== 'theme') return
    if (data.theme !== 'light' && data.theme !== 'dark') return
    hostTheme = data.theme
    root.setAttribute('data-host-theme', hostTheme)
    apply()
  })

  const ready = () =>
    window.parent.postMessage(
      {
        source: 'dreamlake-artifact-child',
        type: 'ready',
        route: { search: location.search, hash: location.hash },
      },
      '*',
    )
  ready()
  // Each client navigation is a new document for the frame only on reloads;
  // announce again on history changes so the route stays in sync.
  window.addEventListener('popstate', ready)
}

start()
