/**
 * Wires the @dreamlake/dockit shell. Imported FIRST, for its side effect, by
 * both renderer entries so `initDocs` runs before anything renders.
 */
import { initDocs, type PageFrontmatter, type DocPageLoader } from '@dreamlake/dockit'

const pageMetadata = import.meta.glob<PageFrontmatter>('./pages/**/+Page.mdx', {
  eager: true, query: '?frontmatter', import: 'default',
})
const pageLoaders = import.meta.glob<Awaited<ReturnType<DocPageLoader>>>('./pages/**/+Page.mdx')
const rawPages = import.meta.env.DEV
  ? import.meta.glob<string>('./pages/**/+Page.mdx', { eager: true, query: '?raw', import: 'default' })
  : undefined

initDocs({
  site: {
    brand: 'vuer-sim',
    subtitle: 'docs',
    repoUrl: 'https://github.com/vuer-ai/vuer-sim',
    docsRepoUrl: 'https://github.com/vuer-ai/vuer-sim',
    docsBranch: 'main',
    breadcrumbRoot: 'vuer-sim',
    url: 'https://vuer-sim.dreamlake.ai',
    skill: 'vuer-sim',
    summary:
      'vuer-sim gives MuJoCo and USD scenes simulation materials: PhysicsMaterial with MJCF and USD converters (restitution through the solref damping ratio), a visual-to-physics lookup table, LiDAR sensor materials with lidar_returns, a JSON MaterialTable stored in a bundle, and a vuer editor (@vuer-ai/vuer-sim).',
    skillTriggers: [
      'setting friction, restitution or density of MuJoCo or USD geoms',
      'converting physics materials between MJCF and USD (UsdPhysics MaterialAPI)',
      'mapping restitution to MuJoCo solref',
      'guessing physics materials from visual material names or PBR parameters',
      'simulating LiDAR returns on glass, black or noisy surfaces',
      'reading, writing or applying a materials.json material table in a scene bundle',
      'building or wiring the vuer-sim material editor (@vuer-ai/vuer-sim)',
    ],
    versionChips: [{ label: 'vuer-sim', version: __APP_VERSION__ }],
    gitHash: __GIT_HASH__,
    docsPagesPath: 'docs/pages',
  },
  pageMetadata,
  pageLoaders,
  rawPages,
  sectionOrder: ['Get started', 'Schema', 'Guides', 'Editor', 'Reference', 'Contributing'],
})
