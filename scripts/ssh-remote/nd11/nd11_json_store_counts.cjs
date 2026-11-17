// ND-11 read-only store counts (audit runbook section 4 step 3 + post-run check).
// Mirrors the harness preflight guard: count docs per storeKey in json_store;
// exit 3 if any key is empty (seed-to-production guard). No writes anywhere.
// Run with cwd = saq-report (uses the app's node_modules + .env; URI never printed).
const path = require('path');
const { createRequire } = require('module');
const requireFromApp = createRequire(path.join(process.cwd(), 'package.json'));
requireFromApp('dotenv').config({ path: path.join(process.cwd(), '.env') });
const { MongoClient } = requireFromApp('mongodb');
const KEYS = ['assistants', 'courses', 'lecturers', 'schedules', 'reports', 'globalConfig'];
(async () => {
    const uri = process.env.MONGO_URL || process.env.MONGO_PUBLIC_URL;
    if (!uri) { console.error('no Mongo URI in env'); process.exit(3); }
    const mc = new MongoClient(uri, { serverSelectionTimeoutMS: 8000 });
    await mc.connect();
    const col = mc.db().collection('json_store');
    const counts = {};
    for (const k of KEYS) counts[k] = await col.countDocuments({ key: k });
    await mc.close();
    console.log('COUNTS_JSON=' + JSON.stringify(counts));
    const empty = KEYS.filter((k) => counts[k] === 0);
    if (empty.length) { console.error('EMPTY_KEYS=' + empty.join(',')); process.exit(3); }
})().catch((e) => { console.error(String((e && e.message) || e)); process.exit(3); });
