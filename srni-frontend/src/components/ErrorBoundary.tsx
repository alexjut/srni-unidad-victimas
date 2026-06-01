import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gov-grisTenue px-4">
        <div className="card max-w-lg w-full text-center py-10 px-6">
          <div className="mx-auto w-14 h-14 rounded-full bg-gov-rojoTenue flex items-center justify-center mb-5">
            <AlertTriangle size={28} className="text-gov-rojo" />
          </div>

          <h1 className="font-display text-xl font-bold text-gray-800 mb-2">
            Algo salió mal
          </h1>
          <p className="text-sm text-gov-gris mb-6">
            Ocurrió un error inesperado. Puedes intentar de nuevo o contactar al administrador si el problema persiste.
          </p>

          {import.meta.env.DEV && this.state.error && (
            <pre className="text-left text-xs bg-gray-50 border border-gov-borde rounded-lg p-4 mb-6 overflow-x-auto text-gov-rojo">
              {this.state.error.message}
            </pre>
          )}

          <button onClick={this.handleReset} className="btn-primary inline-flex items-center gap-2">
            <RotateCcw size={16} />
            Intentar de nuevo
          </button>
        </div>
      </div>
    );
  }
}
