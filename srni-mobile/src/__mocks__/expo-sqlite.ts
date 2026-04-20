/**
 * Mock de expo-sqlite para tests Jest (no hay módulo nativo disponible en Node).
 */
const mockDb = {
  execAsync: jest.fn().mockResolvedValue(undefined),
  runAsync: jest.fn().mockResolvedValue({ lastInsertRowId: 1, changes: 1 }),
  getFirstAsync: jest.fn().mockResolvedValue(null),
  getAllAsync: jest.fn().mockResolvedValue([]),
  withTransactionAsync: jest.fn().mockImplementation((fn: () => Promise<void>) => fn()),
};

export const openDatabaseAsync = jest.fn().mockResolvedValue(mockDb);

export default { openDatabaseAsync };
