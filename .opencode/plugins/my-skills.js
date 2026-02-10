/**
 * Plugin base para OpenCode.
 * Inyecta contexto inicial desde todas las skills disponibles en la carpeta skills.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const stripFrontmatter = (content) => {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  return match ? match[2].trim() : content.trim();
};

export const MySkillsPlugin = async () => {
  const skillsDir = path.resolve(__dirname, '../../skills');
  const loadSkillFiles = () => {
    if (!fs.existsSync(skillsDir)) return [];

    return fs
      .readdirSync(skillsDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith('_'))
      .map((entry) => ({
        name: entry.name,
        file: path.join(skillsDir, entry.name, 'SKILL.md')
      }))
      .filter((entry) => fs.existsSync(entry.file));
  };

  const getBootstrap = () => {
    const skillFiles = loadSkillFiles();
    if (skillFiles.length === 0) return null;

    const merged = skillFiles
      .map(({ name, file }) => {
        const full = fs.readFileSync(file, 'utf8');
        return `# Skill: ${name}\n\n${stripFrontmatter(full)}`;
      })
      .join('\n\n');

    return `<EXTREMELY_IMPORTANT>
You have local skills available.

The content below is already loaded (do not load it twice):

${merged}
</EXTREMELY_IMPORTANT>`;
  };

  return {
    'experimental.chat.system.transform': async (_input, output) => {
      const bootstrap = getBootstrap();
      if (!bootstrap) return;
      (output.system ||= []).push(bootstrap);
    }
  };
};
