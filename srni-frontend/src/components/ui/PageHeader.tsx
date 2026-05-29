interface PageHeaderProps {
  titulo: string;
  subtitulo?: string;
  acciones?: React.ReactNode;
}

export default function PageHeader({ titulo, subtitulo, acciones }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-gray-800">{titulo}</h2>
        {subtitulo && (
          <p className="text-gray-500 text-sm mt-0.5">{subtitulo}</p>
        )}
      </div>
      {acciones && <div className="flex items-center gap-2">{acciones}</div>}
    </div>
  );
}
