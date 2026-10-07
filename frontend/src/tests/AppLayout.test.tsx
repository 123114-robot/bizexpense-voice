import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'

test('application shell exposes skip navigation and labelled landmarks', () => {
  render(
    <MemoryRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<h1>Dashboard content</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )

  expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
    'href',
    '#main-content',
  )
  expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeInTheDocument()
  expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
})
