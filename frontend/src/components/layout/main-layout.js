'use client'

import React from 'react'
import { Sidebar } from './sidebar'

export const MainLayout = ({ children, username, projects }) => {
  return (
    <div className="flex h-screen">
      <Sidebar username={username} projects={projects} />
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
} 