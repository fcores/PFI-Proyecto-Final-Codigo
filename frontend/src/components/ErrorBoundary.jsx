import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught:", error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="page">
          <section className="card state-card" role="alert">
            <h2>Algo salió mal</h2>
            <p className="muted">
              Ocurrió un error inesperado al mostrar esta pantalla. Podés reintentar o volver al inicio.
            </p>
            <div className="buttons state-card__actions">
              <button type="button" className="btn-secondary" onClick={() => window.location.assign("/")}>
                Ir al inicio
              </button>
              <button type="button" className="btn-primary" onClick={() => this.setState({ hasError: false })}>
                Reintentar
              </button>
            </div>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}
