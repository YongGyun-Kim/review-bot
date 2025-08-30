import { PromptManager } from '../../src/core/prompt.manager';
import { promises as fs } from 'fs';

jest.mock('fs', () => ({
  promises: {
    readFile: jest.fn(),
    writeFile: jest.fn(),
    readdir: jest.fn()
  }
}));

describe('PromptManager', () => {
  let promptManager: PromptManager;
  const mockFs = fs as jest.Mocked<typeof fs>;

  beforeEach(() => {
    promptManager = new PromptManager();
    jest.clearAllMocks();
  });

  describe('loadPrompt', () => {
    it('should load prompt from file', async () => {
      const mockPrompt = 'Test prompt with {{code_diff}}';
      mockFs.readFile.mockResolvedValue(mockPrompt);

      const result = await promptManager.loadPrompt('test');

      expect(result).toBe(mockPrompt);
      expect(mockFs.readFile).toHaveBeenCalledWith('./prompts/test.md', 'utf-8');
    });

    it('should fallback to default when prompt not found', async () => {
      const defaultPrompt = 'Default prompt with {{code_diff}}';
      mockFs.readFile
        .mockRejectedValueOnce(new Error('File not found'))
        .mockResolvedValueOnce(defaultPrompt);

      const result = await promptManager.loadPrompt('nonexistent');

      expect(result).toBe(defaultPrompt);
    });
  });

  describe('extractVariables', () => {
    it('should extract variables from template', () => {
      const template = 'Test {{var1}} and {{var2}} and {{var1}} again';
      const variables = (promptManager as any).extractVariables(template);

      expect(variables).toEqual(['var1', 'var2']);
    });
  });

  describe('populatePrompt', () => {
    it('should replace template variables with data', () => {
      const template = 'Files changed: {{files_changed}}, Code: {{code_diff}}';
      const data = {
        gitDiff: {
          stats: { filesChanged: 3, insertions: 10, deletions: 5 },
          commitMessage: 'Test commit',
          branch: 'main',
          files: []
        },
        codeDiff: 'test code'
      };

      const result = promptManager.populatePrompt(template, data);

      expect(result).toContain('Files changed: 3');
      expect(result).toContain('Code: test code');
    });
  });

  describe('validatePrompt', () => {
    it('should validate prompt with required variables', () => {
      const template = 'Review this code: {{code_diff}}';

      const result = promptManager.validatePrompt(template);

      expect(result.valid).toBe(true);
      expect(result.missingVariables).toHaveLength(0);
    });

    it('should fail validation when missing required variables', () => {
      const template = 'Review this code without variables';

      const result = promptManager.validatePrompt(template);

      expect(result.valid).toBe(false);
      expect(result.missingVariables).toContain('{{code_diff}}');
    });
  });
});