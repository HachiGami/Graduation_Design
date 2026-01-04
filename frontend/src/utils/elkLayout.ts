import ELK from 'elkjs/lib/elk.bundled.js'

export interface LayoutNode {
  id: string
  width?: number
  height?: number
}

export interface LayoutEdge {
  id?: string
  source: string
  target: string
}

export interface LayoutOptions {
  direction?: 'RIGHT' | 'DOWN' | 'LEFT' | 'UP'
  nodeSpacing?: number
  layerSpacing?: number
  seed?: number
}

export interface LayoutResult {
  positions: Map<string, { x: number; y: number }>
  width: number
  height: number
}

const DEFAULT_NODE_WIDTH = 120
const DEFAULT_NODE_HEIGHT = 60

export async function computeELKLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: LayoutOptions = {}
): Promise<LayoutResult> {
  const {
    direction = 'RIGHT',
    nodeSpacing = 100,
    layerSpacing = 180,
    seed = 42
  } = options

  const elk = new ELK()

  const elkGraph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': direction,
      'elk.spacing.nodeNode': String(nodeSpacing),
      'elk.layered.spacing.nodeNodeBetweenLayers': String(layerSpacing),
      'elk.layered.nodePlacement.strategy': 'LINEAR_SEGMENTS',
      'elk.layered.layering.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.crossingMinimization.semiInteractive': 'true',
      'elk.randomSeed': String(seed),
      'elk.separateConnectedComponents': 'false',
      'elk.spacing.componentComponent': '80',
      'elk.layered.spacing.edgeNodeBetweenLayers': '60',
      'elk.layered.spacing.edgeEdgeBetweenLayers': '30',
      'elk.edgeRouting': 'ORTHOGONAL'
    },
    children: nodes.map(node => ({
      id: node.id,
      width: node.width || DEFAULT_NODE_WIDTH,
      height: node.height || DEFAULT_NODE_HEIGHT
    })),
    edges: edges.map(edge => ({
      id: edge.id || `${edge.source}-${edge.target}`,
      sources: [edge.source],
      targets: [edge.target]
    }))
  }

  const layout = await elk.layout(elkGraph)

  const positions = new Map<string, { x: number; y: number }>()
  
  if (layout.children) {
    for (const child of layout.children) {
      if (child.x !== undefined && child.y !== undefined) {
        positions.set(child.id, {
          x: child.x + (child.width || DEFAULT_NODE_WIDTH) / 2,
          y: child.y + (child.height || DEFAULT_NODE_HEIGHT) / 2
        })
      }
    }
  }

  return {
    positions,
    width: layout.width || 0,
    height: layout.height || 0
  }
}

