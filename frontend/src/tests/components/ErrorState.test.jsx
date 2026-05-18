import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ErrorState } from '../../components/status/ErrorState.jsx';
import { getErrorState } from '../../view-models/errorCatalog.js';

describe('ErrorState', () => {
  it('renders standardized action, technical code and logging metadata', () => {
    const error = {
      ...getErrorState('API_UNREACHABLE'),
      code: 'API_UNREACHABLE',
      classification: 'API_UNREACHABLE',
      details: {},
      status: null,
    };

    const { container } = render(<ErrorState error={error} />);
    const root = container.querySelector('.state-card--error');

    expect(screen.getByRole('heading', { name: 'Backend nicht erreichbar' })).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: API_UNREACHABLE')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: API_UNREACHABLE')).toBeInTheDocument();
    expect(screen.getByText('Aktion: Erneut versuchen')).toBeInTheDocument();
    expect(root).toHaveAttribute('data-technical-code', 'API_UNREACHABLE');
    expect(root).toHaveAttribute('data-retry', 'true');
    expect(root).toHaveAttribute('data-log-event', 'gui_api_unreachable');
  });

  it('does not render a retry button unless an explicit action handler is provided', () => {
    const error = {
      ...getErrorState('FORBIDDEN'),
      code: 'FORBIDDEN',
      classification: 'FORBIDDEN',
      details: {},
      status: 403,
    };

    render(<ErrorState error={error} />);

    expect(screen.getByText('Aktion: Berechtigung pruefen')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
