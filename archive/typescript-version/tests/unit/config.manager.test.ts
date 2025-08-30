import { ConfigManager } from '../../src/core/config.manager';
import { promises as fs } from 'fs';
import { join } from 'path';

jest.mock('fs', () => ({
  promises: {
    readFile: jest.fn(),
    writeFile: jest.fn(),
    access: jest.fn()
  }
}));

describe('ConfigManager', () => {
  let configManager: ConfigManager;
  const mockFs = fs as jest.Mocked<typeof fs>;

  beforeEach(() => {
    configManager = new ConfigManager();
    jest.clearAllMocks();
  });

  describe('loadConfig', () => {
    it('should load default config when no config file exists', async () => {
      mockFs.readFile.mockRejectedValue(new Error('File not found'));

      const config = await configManager.loadConfig();

      expect(config.provider).toBe('claude');
      expect(config.apiKey).toBe('');
      expect(config.promptTemplate).toBe('default');
    });

    it('should merge local and global configs', async () => {
      mockFs.readFile
        .mockResolvedValueOnce('{"provider": "chatgpt"}') // global config
        .mockResolvedValueOnce('{"apiKey": "test-key"}'); // local config

      const config = await configManager.loadConfig();

      expect(config.provider).toBe('chatgpt');
      expect(config.apiKey).toBe('test-key');
    });
  });

  describe('validateConfig', () => {
    it('should return valid for correct config', () => {
      const config = {
        provider: 'claude' as const,
        apiKey: 'test-key',
        outputDir: './reviews',
        maxFilesPerReview: 10,
        maxTokens: 4000
      };

      const result = configManager.validateConfig(config);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should return errors for invalid config', () => {
      const config = {
        provider: 'claude' as const,
        apiKey: '',
        outputDir: '',
        maxFilesPerReview: -1,
        maxTokens: 0
      };

      const result = configManager.validateConfig(config);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('saveConfig', () => {
    it('should save config to file', async () => {
      const config = { provider: 'claude' as const, apiKey: 'test-key' };
      mockFs.readFile.mockResolvedValue('{}');
      mockFs.writeFile.mockResolvedValue();

      await configManager.saveConfig(config);

      expect(mockFs.writeFile).toHaveBeenCalled();
    });
  });
});