import { Link } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gov-grisTenue px-4 animate-fade-in">
      <div className="text-center max-w-md">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gov-azulTenue flex items-center justify-center mb-6">
          <FileQuestion size={32} className="text-gov-azul" />
        </div>

        <h1 className="font-display text-6xl font-bold text-gov-azulOscuro mb-2">404</h1>
        <h2 className="font-display text-xl font-semibold text-gray-700 mb-3">
          Página no encontrada
        </h2>
        <p className="text-sm text-gov-gris mb-8">
          La página que buscas no existe o fue movida. Verifica la dirección o regresa al inicio.
        </p>

        <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2 transition-all hover:scale-105">
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
