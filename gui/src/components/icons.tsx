import React from 'react'

type P = { size?: number; className?: string }

export const BoltIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="currentColor" stroke="none" opacity={0.95} />
  </svg>
)
export const CrownIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M3 17l3-7 4 4 4-8 4 8 4-4-3 7H3z" />
    <path d="M5 20h14" />
  </svg>
)
export const LayersIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <path d="M12 3L3 9l9 6 9-6-9-6z" /><path d="M3 14l9 6 9-6" /><path d="M3 19l9 6 9-6" opacity={0.55} />
  </svg>
)
export const BranchIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="12" cy="18" r="2.5" />
    <path d="M6 8.5V12a4 4 0 004 4h4a4 4 0 004-4V8.5" />
  </svg>
)
export const SearchIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4" />
  </svg>
)
export const UsersIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <path d="M15 11a3 3 0 100-6 3 3 0 000 6z" /><path d="M8 13a3 3 0 100-6 3 3 0 000 6z" /><path d="M8 14c-2 0-4 1-4 3.5V19h8v-1.5C12 15 10 14 8 14z" /><path d="M15 12c-1.2 0-2.2.4-3 1 .6.6 1 1.4 1 2.5V19h6v-1.5c0-2-2-3-4-3z" />
  </svg>
)
export const MergeIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <circle cx="6" cy="6" r="2.2" /><circle cx="18" cy="6" r="2.2" /><circle cx="12" cy="18" r="2.8" />
    <path d="M6 8.3V12c0 2 1.2 3.8 3 4.7" /><path d="M18 8.3V12c0 2-1.2 3.8-3 4.7" />
  </svg>
)
export const CheckIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M6 13l3 3 9-9" />
  </svg>
)
export const SendIcon: React.FC<P> = ({ size = 16, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 2L11 13" /><path d="M22 2L15 22 11 13 2 9l20-7z" />
  </svg>
)
export const CopyIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <rect x="9" y="9" width="10" height="10" rx="2" /><path d="M5 15V7a2 2 0 012-2h8" />
  </svg>
)
export const XIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
)
export const ChevronRightIcon: React.FC<P> = ({ size = 12, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className={className}>
    <path d="M9 6l6 6-6 6" />
  </svg>
)
export const NetworkIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <circle cx="12" cy="12" r="2.5" /><circle cx="5" cy="5" r="1.8" /><circle cx="19" cy="5" r="1.8" /><circle cx="19" cy="19" r="1.8" /><circle cx="5" cy="19" r="1.8" />
    <path d="M7 7l3 3M17 7l-3 3M7 17l3-3M17 17l-3-3" />
  </svg>
)
export const MessageIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <path d="M21 15a2 2 0 01-2 2H8l-5 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
  </svg>
)
export const AlertIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
    <path d="M12 8v6M12 18h.01" /><path d="M10.2 3.2L3.1 15.2A2 2 0 004.9 18.5H19a2 2 0 001.8-3.3L13.8 3.2a2 2 0 00-3.6 0z" />
  </svg>
)
export const ActivityIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className}>
    <path d="M2 13h5l2-6 4 12 2-6h7" />
  </svg>
)
export const SparkleIcon: React.FC<P> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className={className}>
    <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3z" /><path d="M19 13l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z" /><path d="M5 15l1 1.2 1.2 1-1.2 1L5 19l-1-0.8L2.8 17l1.2-1L5 15z" />
  </svg>
)
