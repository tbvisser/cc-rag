import {
  Map,
  LayoutDashboard,
  FolderKanban,
  Activity,
  BarChart3,
  ShieldAlert,
  Target,
  Shield,
  Award,
  Network,
  Box,
  GitBranch,
  Search,
  Upload,
  Download,
  RotateCcw,
  UserCircle,
  Settings,
  Info,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  path: string
  hasBackend: boolean
}

export interface NavSection {
  id: string
  label: string
  icon: LucideIcon
  items: NavItem[]
}

export const navSections: NavSection[] = [
  {
    id: 'supply-chain',
    label: 'My Supply Chain',
    icon: Network,
    items: [
      { id: 'sc-map', label: 'Map', icon: Map, path: '/supply-chain/map', hasBackend: false },
      { id: 'sc-dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/supply-chain/dashboard', hasBackend: false },
      { id: 'sc-projects', label: 'Projects', icon: FolderKanban, path: '/supply-chain/projects', hasBackend: false },
    ],
  },
  {
    id: 'industry',
    label: 'My Industry',
    icon: Activity,
    items: [
      { id: 'ind-status', label: 'Current status', icon: Activity, path: '/industry/status', hasBackend: false },
      { id: 'ind-analysis', label: 'Analysis', icon: BarChart3, path: '/industry/analysis', hasBackend: false },
      { id: 'ind-risk', label: 'Risk Monitor', icon: ShieldAlert, path: '/industry/risk', hasBackend: false },
    ],
  },
  {
    id: 'context',
    label: 'My Context',
    icon: Target,
    items: [
      { id: 'ctx-strategy', label: 'Strategy', icon: Target, path: '/context/strategy', hasBackend: false },
      { id: 'ctx-resilience', label: 'Resilience', icon: Shield, path: '/context/resilience', hasBackend: false },
      { id: 'ctx-maturity', label: 'Maturity', icon: Award, path: '/context/maturity', hasBackend: false },
    ],
  },
  {
    id: 'graph',
    label: 'Supply chain graph',
    icon: GitBranch,
    items: [
      { id: 'graph-overview', label: 'Overview', icon: Network, path: '/graph/overview', hasBackend: false },
      { id: 'graph-entity', label: 'Entity Model', icon: Box, path: '/graph/entity', hasBackend: false },
      { id: 'graph-view', label: 'Graph View', icon: GitBranch, path: '/graph/view', hasBackend: false },
      { id: 'graph-search', label: 'Search', icon: Search, path: '/graph/search', hasBackend: false },
    ],
  },
  {
    id: 'schema',
    label: 'Schema Management',
    icon: Upload,
    items: [
      { id: 'schema-upload', label: 'Upload Schema', icon: Upload, path: '/schema/upload', hasBackend: true },
      { id: 'schema-download', label: 'Download Schema', icon: Download, path: '/schema/download', hasBackend: false },
      { id: 'schema-reset', label: 'Reset to Default', icon: RotateCcw, path: '/schema/reset', hasBackend: false },
    ],
  },
]

export const bottomNavItems: NavItem[] = [
  { id: 'account', label: 'My Account', icon: UserCircle, path: '/account', hasBackend: false },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings', hasBackend: false },
  { id: 'about', label: 'About', icon: Info, path: '/about', hasBackend: false },
]
