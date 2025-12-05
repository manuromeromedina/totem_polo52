import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const apiUrl = process.env.API_URL || 'http://localhost:8000';

const generateContent = (production) => `export const environment = {
  production: ${production},
  apiUrl: '${apiUrl}'
};
`;

const targetDev = resolve('src/environments/environment.ts');
const targetProd = resolve('src/environments/environment.prod.ts');

writeFileSync(targetDev, generateContent(false), 'utf8');
writeFileSync(targetProd, generateContent(true), 'utf8');

console.log(`[env] environment files actualizados con API_URL=${apiUrl}`);
