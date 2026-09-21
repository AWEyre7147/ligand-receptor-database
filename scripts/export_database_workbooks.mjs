// Render bounded preview images from canonical Python-generated worksheet samples.
// Usage: node export_database_workbooks.mjs <config.json>
// Requires the optional @oai/artifact-tool runtime; produces PNGs, never final XLSX.
// Unhandled parse/render errors exit nonzero, preventing a preview-enabled promotion.
import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const config = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
const wb = Workbook.create();
for (let index = 0; index < config.sheets.length; index++) {
  const spec = config.sheets[index];
  const data = JSON.parse(await fs.readFile(spec.path, 'utf8'));
  const sheet = wb.worksheets.add(spec.name);
  const n = data.rows.length + 1, m = data.columns.length;
  console.log(`${spec.name}: ${n - 1} rows`);
  sheet.getRangeByIndexes(0, 0, 1, m).values = [data.columns];
  for (let start = 0; start < data.rows.length; start += 3000) {
    const batch = data.rows.slice(start, start + 3000);
    sheet.getRangeByIndexes(start + 1, 0, batch.length, m).values = batch;
  }
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(spec.name === 'Ligand-Receptor' || spec.name === 'Nonprotein-Proxy' ? 2 : 1);
  sheet.getRangeByIndexes(0,0,1,m).format = {fill:'#203F60', font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:34,horizontalAlignment:'center',verticalAlignment:'center'};
  const widths = [];
  for (let col = 0; col < m; col++) {
    const header = data.columns[col];
    const width = spec.name === 'Readme' && col === 1 ? 110 : /ligand$|receptor$|display_label|source_label/.test(header) ? 25 : /description|reason|limitation|citation|context|identity|value$/.test(header) ? 48 : /_id$|_key$/.test(header) ? 38 : 24;
    widths.push(width);
    const range = sheet.getRangeByIndexes(0,col,n,1);
    range.format.columnWidth = width;
    range.setNumberFormat(data.types[col] === 'number' ? '#,##0' : data.types[col] === 'boolean' ? 'General' : '@');
  }
  if (n > 1) {
    sheet.getRangeByIndexes(1,0,n-1,m).format.font = {name:'Arial',size:10};
    // Long text is fully retained; wrap the visible data rows, with ample Readme height.
    sheet.getRangeByIndexes(1,0,n-1,m).format.wrapText = true;
    sheet.getRangeByIndexes(1,0,n-1,m).format.verticalAlignment = 'top';
    for(let i=0;i<data.rows.length;i++) {
      const height=Math.max(20,...data.rows[i].map((v,j)=>typeof v === 'string' ? Math.min(300,Math.ceil(v.length/Math.max(1,widths[j]-2))*13):20));
      sheet.getRangeByIndexes(i+1,0,1,m).format.rowHeight=height;
    }
  }
  if (index < 2) sheet.tabColor = '#203F60';
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:"'Ligand-Receptor'!A1:D4",include:'values,formulas',maxChars:1500,tableMaxRows:4,tableMaxCols:4})).ndjson);
await fs.mkdir(config.previewDir, {recursive:true});
for (const spec of config.sheets) {
  const preview = await wb.render({sheetName:spec.name,range:spec.name === 'Readme' ? 'A1:B7' : 'A1:D6',scale:1,format:'png'});
  await fs.writeFile(path.join(config.previewDir, spec.name + '.png'),new Uint8Array(await preview.arrayBuffer()));
}
// Full-workbook export is unavailable for this dataset size (Invalid string length).
// These bounded previews check layout; Python streams the complete canonical tables.
