/**
 * Mock de expo-sqlite para tests Jest (no hay módulo nativo disponible en Node).
 */
const mockDb = {
  execAsync: jest.fn().mockResolvedValue(undefined),
  runAsync: jest.fn().mockResolvedValue({ lastInsertRowId: 1, changes: 1 }),
  getFirstAsync: jest.fn().mockResolvedValue(null),
  getAllAsync: jest.fn().mockResolvedValue([]),
  withTransactionAsync: jest.fn().mockImplementation((fn: () => Promise<void>) => fn()),
  // Statement preparado (inserción por lotes): prepareAsync devuelve un statement
  // reutilizable con executeAsync por fila y finalizeAsync al terminar.
  prepareAsync: jest.fn().mockResolvedValue({
    executeAsync: jest.fn().mockResolvedValue({ lastInsertRowId: 1, changes: 1 }),
    finalizeAsync: jest.fn().mockResolvedValue(undefined),
  }),
};

export const openDatabaseAsync = jest.fn().mockResolvedValue(mockDb);

export default { openDatabaseAsync };
