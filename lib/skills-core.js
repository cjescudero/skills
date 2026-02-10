import fs from 'fs';
import path from 'path';

export function extractFrontmatter(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) return { name: '', description: '', content };

    const frontmatter = {};
    for (const line of match[1].split('\n')) {
      const sep = line.indexOf(':');
      if (sep <= 0) continue;
      const key = line.slice(0, sep).trim();
      const value = line.slice(sep + 1).trim().replace(/^['"]|['"]$/g, '');
      frontmatter[key] = value;
    }

    return {
      name: frontmatter.name || '',
      description: frontmatter.description || '',
      content: match[2].trim()
    };
  } catch {
    return { name: '', description: '', content: '' };
  }
}

export function listSkills(skillsRoot) {
  if (!fs.existsSync(skillsRoot)) return [];

  return fs
    .readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const skillFile = path.join(skillsRoot, entry.name, 'SKILL.md');
      if (!fs.existsSync(skillFile)) {
        return { name: entry.name, description: '', skillFile: null };
      }
      const { name, description } = extractFrontmatter(skillFile);
      return { name: name || entry.name, description, skillFile };
    });
}
