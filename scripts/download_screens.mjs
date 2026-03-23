import { createWriteStream, mkdirSync } from 'fs';
import { pipeline } from 'stream/promises';

const OUT = 'design/screens';
mkdirSync(OUT, { recursive: true });

const screens = [
  {
    slug: 'dashboard',
    title: 'Final Dashboard — Obsidian Ledger',
    id: '2277c47567854717a7fa3e00e92fb99b',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2NiMGRiOGRjNDM1ODRkZDA5MDIxZTk5ZTBiYjg2NWZkEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uidsW1KvktCCgYNn7q9OlpPq7reexTZ9PuW7uWx72oKCU5au3UjCsT_Y4nvhUczJbaAWnN_Ej9tiMolcQA5UQ6JobTyUqprIcxljQU3n8gUsBUysffQr5AHQ6MhC3C25sj3KI37R5Bn5dZBpjxKCuRnUce-RhVHP8pRCtjTqiUNWqdh2sbdZqndcJVLcszdPruXDrwllTaVLUKFbKIvgO-Dko54KNAcaW6YSxdEX5WpmNIB3dUPvOFg7smv',
  },
  {
    slug: 'signals',
    title: 'Final Signals & Activity',
    id: '4b0ba5c1aad34fe686727fb31e538cbc',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2NlZjdhNTA1ZDE3MjQwMDdiZGQyMmM2ZmRjNjIzZTk5EgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0ug2_SkElFdPdURDmidBc4HjM1IkHnDkzG-uOziLGN2wjKFuDUp1Nz1vOhKY1zaXPaluHv75IR2R4Oee1AMhCMi2jYEddznmtuaQyQ0wahCX3ReLytFboAyvcRqrnt0hIv1A4MSNPlaw4ceaN382FvPNNhce2tHJBU1tH0OPDhKlJibP1g-iNWm7QznJH_gQ3NB66HPpeReTSgiRrXnKeOSg0NEL8qOY_XJ3r-ouHL-8C06kyZmODFpqiXk',
  },
  {
    slug: 'assets',
    title: 'Final Assets & Valuations',
    id: 'e21d3b24395041269140399b703abf6a',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzE5NDgzNWEyMjQxMDQzMGQ5NDY0ZjUwODM0MWIxNzhjEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uiRjFkYd9OkKgYSjwGIhoxOaZ8ARt7fDqxMfvW7o3igh3Rm6iL6TFRAS18fww_g72RQ0FVKC264BV4viipFEwVp4BRjZYm6UTiIDIwCj2eyZocc03-ElM16Mhmfhv2UPz2QcYM0U67gWvxdFie2Bz_GLDjIB_-cmtPmmUClaUkFCeJRehKZDoBchefPg3YI-D1dq_jDYEMMDNLd0wOWmfmn4BsLDT8qEyypeFFVeCAuQSLsZ5Zs7-SPlag',
  },
  {
    slug: 'performance',
    title: 'Final Performance Analytics',
    id: '290fff9636ba460287367a74a5b5ebfa',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2Y3NDY5NWFmZTYxYzRjODNhYzQ5OTM5M2JhYzc3NDg4EgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0ujDtJEscvQlaeZpOXLEnrVTrndVMSoPGUyHgzPScZCwEORiWQB5cVOxdAyZVz2vZKN3rbZvPz5UvjSjK-czY7EYoHNzBLpZ_McfTkdoCc57qMFKcVRkIFgWcWwCfb4ajguFqWKoXp132Ao70QeGOjoxwmcaHgZJkGX7SaWrzndpRQUNXFmPKxSFgP6G20_Q_wr1PgdxzOjbtiap2xfJyYYSc7_sHnsu3saUcBoMfjtYwi_qaqwZAk7QiPg',
  },
  {
    slug: 'projections',
    title: 'Final Projections — Monte Carlo',
    id: 'fa14630e602942fc88b00a661d607752',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzcxMDNlYTMyY2ExMzQ1MmY5ZTdkNDNiOGQ1MzVmZGRlEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uihspmhhGOkJGGMizijw8rL1Q-57XCUIC5QzsUjE1tsRGj29-X9RWFxCBsX_J5FyMZBNO98CjFOkwit1VDvQeAP9x1GqRzputHHuV5Tt7LAElZiXBsF2iprN94ZCCdwHwDuS70hYe0unOGJITjttGmmK0B0LrSJWDToA7PWEYsOesBbDPYNef20iVnoLV793BcOHx0VBAzfeQQJFvRuBM4PVAGP4Zq8go0M2wA8rCP_4OA9ROuRPz3OdP0',
  },
  {
    slug: 'tax',
    title: 'Final Tax Optimization',
    id: 'bee56bf51ced4454a69aee8033e8addc',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzQxNzAxOGZmNTljNDQzZGE5ZWZhM2JiMzkyZWI5NzIwEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0ugah7v0WbcLA64AkMY0QO6eGsvqCUh0yyTtTmMxgPK_wgy0M9Q199hnbBUcKrPcqOwanQyfqRF3SP6D2D0WHLvqPSJwn-EyqRO1xtr7ghudH2ZHPyMNTmzxd6BrNjrWuHrOx7EavglgwbDZvvZ1neUXw6g1zqdzGuQfAHn-ev5heUhy8MZTFm6Z0dri1dsLhPs31NxT7Bscu0aCJ3uLQOwNVEHPW57NNK2jLU0bEqIJpyYZpvZLOon1xGMi',
  },
  {
    slug: 'journal',
    title: 'Final Decision Journal',
    id: 'c2e71169585c46f3b664929c4d91dc85',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzZkOTE5YmZmYjEyMzQyZmVhNmYxZWU1M2NiZmVmMzg1EgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uh1CLU_kSKXLqkQT6DQKpMRX4aa8It3bdh5c-YWBwlHJsKo3smrU3lbB-V7O0nGHBwY2ZCyD-43d8Fwb7KHu6uHgBZt7K1yMCaQWhtNpqe1hp5S9MLJygLPoju-eftxHOKpr8RzrvT7_zFeSQm7QZ9WV_O53hGhMIexhbZghGEcRrRgJh_N8XhxuDR8wY088mEalnpemyNIvqf_Hc1RL0xTV88CVAU09e5XTNiKICBVFsr0Km4sXhiytV7i',
  },
  {
    slug: 'config',
    title: 'Final Portfolio Configuration',
    id: 'cfa6eb76b5444f32a9b01ed8d3baec1d',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzk2ZDIwNDMwY2Q4YTQ0Zjc5ZGI5NWRkY2U2MTZlNjNhEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uiB68I9fhxG23lyLCBTJnCwwwaI3eli_cIRPLgJ9zng4OhCJ-39d7tRdKwhnZqeIN1oH-UYCkA8zVehOcSVbKou0xJsCfu3DvJ7v39QOEI0UCg2ekI9Vakj7H1gopeDZKTrf_uGg252s-Rb2oxsbEZFbDednns4kIgcCl3JWjFCT4u_rPGVp_xPJTqIjbYXTzO2qJ7bKNuFmGn7f5K5XlE-dB89PvJTyhm5hgUpY6mHZ9kkDun2u3TB4Dsp',
  },
  {
    slug: 'watchlist',
    title: 'Market Watchlist',
    id: 'ca527bbea2df4c4c9de26919580809b7',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzNjZjM5NjMyOTY2YjQ4YTliYjZjYWNmMTViZTM3MjhiEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0uhgSp-CjGuYqOEakrIbDKjEclWY-BqWwvi8Ohy34Aq4DWQYCU8YQaB_Y8GtzwkinWo4DBHa26IHVxpjWi4SP0mOsDinowmHCUDaQC1TV0qg2OTPWPvOaxlzlLKicdQJlac47Q7XnaNe_2C5shhSDTYjD2PJCwXghGFyGhgO92NaccXeovH9Wm1URGeOeA7qYFSc_i4_kJhyxXZzjjyxITuG1yDKRUsMuHJxjWe3LyMo3lpTbkwLZL3PdLPG',
  },
  {
    slug: 'ai_insights',
    title: 'AI Insights',
    id: 'c3041f17e9e1418fb8ad3ef936c78486',
    htmlUrl: 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzQ3ZjAzYzEzNmRiYjRkNjBiNzVhZjZjMjM1MmQ3NzJmEgsSBxCB85eIiwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMTU4MDQxOTc1OTE5MTI1MzA2Mg&filename=&opi=89354086',
    pngUrl: 'https://lh3.googleusercontent.com/aida/ADBb0ujaPR_0EJ5G3tR1LvhDXPRoGteYaBbwqWq5A7SQnKV_c3AgfdfZFm3NzG4WX7aDl6eeYMhEjE30cPr38sQ6ipeCNpBXy9ksc3uLNZ9DVUWcL2vgJoaO1QhtaJBNFosaU1PGqxcm3WPXzA58SAUpUmRaVZJRTxKl2SxNUQJogG4iTvy2Cwa-cUhDoSGJUwa7uo39WF8j14kXcxaWLyScfqDJS44MgMQBo26SCRHpzKf1VpXKeqIxMRKyJRHK',
  },
];

async function downloadFile(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ws = createWriteStream(dest);
  await pipeline(res.body, ws);
}

let ok = 0, fail = 0;
for (const s of screens) {
  try {
    await downloadFile(s.htmlUrl, `${OUT}/${s.slug}.html`);
    process.stdout.write(`✓ ${s.slug}.html\n`);
    ok++;
  } catch(e) {
    process.stdout.write(`✗ ${s.slug}.html: ${e.message}\n`);
    fail++;
  }
  if (s.pngUrl) {
    try {
      await downloadFile(s.pngUrl, `${OUT}/${s.slug}.png`);
      process.stdout.write(`✓ ${s.slug}.png\n`);
      ok++;
    } catch(e) {
      process.stdout.write(`✗ ${s.slug}.png: ${e.message}\n`);
      fail++;
    }
  }
}
console.log(`\nDone: ${ok} ok, ${fail} failed`);
