import { Component } from 'react';

import { ErrorState } from './ErrorState.jsx';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return {
      error: {
        code: 'UI_RENDER_FAILED',
        title: 'Oberflaeche konnte nicht geladen werden',
        message: error instanceof Error ? error.message : 'Ein unerwarteter UI-Fehler ist aufgetreten.',
        details: {},
        status: null,
      },
    };
  }

  componentDidCatch(error, errorInfo) {
    if (typeof this.props.onError === 'function') {
      this.props.onError(error, errorInfo);
    }
  }

  render() {
    if (this.state.error) {
      return <ErrorState error={this.state.error} />;
    }

    return this.props.children;
  }
}
