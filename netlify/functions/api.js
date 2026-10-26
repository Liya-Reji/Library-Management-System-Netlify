/**
 * Netlify Serverless Function: api.js
 * Compatible Node.js runtime for Netlify Functions.
 * 
 * Provides complete REST API endpoints for Library Management System:
 * - /api/auth/login, /api/auth/register, /api/auth/me, /api/auth/logout
 * - /api/stats
 * - /api/books, /api/books/:id
 * - /api/students, /api/students/:id
 * - /api/issue, /api/return/:id, /api/issued, /api/history
 * - /api/student/dashboard, /api/student/my-books, /api/student/history
 */

const crypto = require('crypto');
const { Pool } = require('pg');

let pool = null;

function normalizeDatabaseUrl(url) {
    if (!url) return null;
    let clean = url.trim();
    if (clean.startsWith('postgres://')) {
        clean = clean.replace('postgres://', 'postgresql://');
    }
    return clean;
}

function getPool() {
    const dbUrl = normalizeDatabaseUrl(process.env.DATABASE_URL);
    if (!dbUrl) {
        return null;
    }
    if (!pool) {
        pool = new Pool({
            connectionString: dbUrl,
            ssl: { rejectUnauthorized: false },
            connectionTimeoutMillis: 8000,
            max: 5
        });
        pool.on('error', (err) => {
            console.error('Unexpected pg client error', err);
        });
    }
    return pool;
}

// Password verification compatible with Werkzeug (scrypt and pbkdf2)
function verifyPassword(hash, password) {
    if (!hash || !password) return false;
    try {
        const parts = hash.split('$');
        if (parts[0].startsWith('scrypt:')) {
            const [, N, r, p] = parts[0].split(':');
            const salt = parts[1];
            const expected = parts[2];
            const derived = crypto.scryptSync(password, salt, 64, {
                N: parseInt(N, 10),
                r: parseInt(r, 10),
                p: parseInt(p, 10),
                maxmem: 128 * parseInt(N, 10) * parseInt(r, 10) * 2
            }).toString('hex');
            return crypto.timingSafeEqual(Buffer.from(derived), Buffer.from(expected));
        }
        if (parts[0].startsWith('pbkdf2:')) {
            const [, algo, iter] = parts[0].split(':');
            const salt = parts[1];
            const expected = parts[2];
            const derived = crypto.pbkdf2Sync(password, salt, parseInt(iter, 10), expected.length / 2, algo).toString('hex');
            return crypto.timingSafeEqual(Buffer.from(derived), Buffer.from(expected));
        }
    } catch (e) {
        console.error('Password verification error', e);
    }
    return false;
}

function hashPassword(password) {
    const salt = crypto.randomBytes(16).toString('hex');
    const N = 32768, r = 8, p = 1;
    const derived = crypto.scryptSync(password, salt, 64, {
        N, r, p,
        maxmem: 128 * N * r * 2
    }).toString('hex');
    return `scrypt:${N}:${r}:${p}$${salt}$${derived}`;
}

// Session signing and parsing
const SECRET_KEY = process.env.SECRET_KEY || 'lib-mgmt-sys-secret-key-2026';

function signSession(userId) {
    const payload = Buffer.from(JSON.stringify({ userId, ts: Date.now() })).toString('base64');
    const signature = crypto.createHmac('sha256', SECRET_KEY).update(payload).digest('hex');
    return `${payload}.${signature}`;
}

function verifySession(sessionToken) {
    if (!sessionToken) return null;
    try {
        const [payload, signature] = sessionToken.split('.');
        if (!payload || !signature) return null;
        const expectedSig = crypto.createHmac('sha256', SECRET_KEY).update(payload).digest('hex');
        if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expectedSig))) {
            return null;
        }
        const data = JSON.parse(Buffer.from(payload, 'base64').toString('utf8'));
        return data.userId;
    } catch (e) {
        return null;
    }
}

function parseCookies(headers) {
    const list = {};
    const cookieHeader = headers.cookie || headers.Cookie;
    if (!cookieHeader) return list;
    cookieHeader.split(';').forEach(cookie => {
        let [name, ...rest] = cookie.split('=');
        name = name.trim();
        if (!name) return;
        const value = rest.join('=').trim();
        list[name] = decodeURIComponent(value);
    });
    return list;
}

function buildResponse(statusCode, body, headers = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': headers['Access-Control-Allow-Origin'] || '*',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
    };

    const mergedHeaders = { ...defaultHeaders, ...headers };
    return {
        statusCode,
        headers: mergedHeaders,
        body: typeof body === 'string' ? body : JSON.stringify(body)
    };
}

exports.handler = async function (event, context) {
    const method = event.httpMethod ? event.httpMethod.toUpperCase() : 'GET';

    // Handle CORS preflight
    if (method === 'OPTIONS') {
        return buildResponse(204, '');
    }

    // Resolve path
    let path = event.path || '/';
    if (event.rawUrl) {
        try {
            const urlObj = new URL(event.rawUrl);
            if (urlObj.pathname && !urlObj.pathname.startsWith('/.netlify/functions/api')) {
                path = urlObj.pathname;
            }
        } catch (e) {}
    }

    // Normalize path: strip /.netlify/functions/api
    if (path.startsWith('/.netlify/functions/api')) {
        path = path.replace('/.netlify/functions/api', '') || '/';
    }
    // Normalize /api prefix
    if (path.startsWith('/api')) {
        path = path.replace(/^\/api/, '') || '/';
    }
    if (!path.startsWith('/')) {
        path = '/' + path;
    }

    // Parse body
    let body = {};
    if (event.body) {
        try {
            body = event.isBase64Encoded
                ? JSON.parse(Buffer.from(event.body, 'base64').toString('utf8'))
                : JSON.parse(event.body);
        } catch (e) {
            body = {};
        }
    }

    const queryParams = event.queryStringParameters || {};
    const cookies = parseCookies(event.headers || {});
    const currentUserId = verifySession(cookies.session);

    // Root and Health Check
    if (path === '/' || path === '' || path === '/health') {
        const dbConfigured = Boolean(process.env.DATABASE_URL);
        return buildResponse(200, {
            status: 'ok',
            service: 'Library Management System Netlify API',
            runtime: 'Node.js Serverless Function',
            database_configured: dbConfigured,
            version: '2.0.0'
        });
    }

    // Check Persistent Database Connection
    const pool = getPool();
    if (!pool) {
        return buildResponse(503, {
            success: false,
            error: 'DATABASE_NOT_CONFIGURED',
            message: 'DATABASE_URL environment variable is not configured. Set DATABASE_URL to your persistent PostgreSQL database in Netlify Site Configuration.'
        });
    }

    let client;
    try {
        client = await pool.connect();
    } catch (dbErr) {
        console.error('PostgreSQL Connection Error:', dbErr.message);
        return buildResponse(503, {
            success: false,
            error: 'DATABASE_CONNECTION_ERROR',
            message: `Could not connect to PostgreSQL database: ${dbErr.message}. Verify DATABASE_URL in Netlify.`
        });
    }

    try {
        // --- 1. AUTH / ME ---
        if (path === '/auth/me' || path === '/me') {
            if (!currentUserId) {
                return buildResponse(200, { authenticated: false });
            }
            const userRes = await client.query('SELECT id, username, email, role FROM users WHERE id = $1', [currentUserId]);
            if (userRes.rows.length === 0) {
                return buildResponse(200, { authenticated: false });
            }
            const user = userRes.rows[0];
            let student = null;
            if (user.role === 'student') {
                const stuRes = await client.query('SELECT * FROM students WHERE user_id = $1', [user.id]);
                if (stuRes.rows.length > 0) student = stuRes.rows[0];
            }
            return buildResponse(200, { authenticated: true, user, student });
        }

        // --- 2. AUTH / LOGIN ---
        if ((path === '/auth/login' || path === '/login') && method === 'POST') {
            const identifier = (body.identifier || body.username || body.email || '').trim();
            const password = body.password || '';

            if (!identifier || !password) {
                return buildResponse(400, {
                    success: false,
                    message: 'Username/email and password are required.'
                });
            }

            const userRes = await client.query(
                'SELECT id, username, email, password_hash, role FROM users WHERE LOWER(username) = LOWER($1) OR LOWER(email) = LOWER($1) LIMIT 1',
                [identifier]
            );

            if (userRes.rows.length === 0) {
                return buildResponse(401, {
                    success: false,
                    message: 'Invalid username/email or password.'
                });
            }

            const user = userRes.rows[0];
            const matches = verifyPassword(user.password_hash, password);
            if (!matches) {
                return buildResponse(401, {
                    success: false,
                    message: 'Invalid username/email or password.'
                });
            }

            const token = signSession(user.id);
            let student = null;
            if (user.role === 'student') {
                const stuRes = await client.query('SELECT * FROM students WHERE user_id = $1 LIMIT 1', [user.id]);
                if (stuRes.rows.length > 0) student = stuRes.rows[0];
            }

            const cookieHeader = `session=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800`;
            return {
                statusCode: 200,
                headers: {
                    'Content-Type': 'application/json',
                    'Set-Cookie': cookieHeader,
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true'
                },
                body: JSON.stringify({
                    success: true,
                    message: `Welcome back, ${user.username}!`,
                    user: {
                        id: user.id,
                        username: user.username,
                        email: user.email,
                        role: user.role
                    },
                    student
                })
            };
        }

        // --- 3. AUTH / REGISTER (STUDENT) ---
        if ((path === '/auth/register' || path === '/register') && method === 'POST') {
            const username = (body.username || '').trim();
            const fullName = (body.full_name || '').trim();
            const studentIdNumber = (body.student_id_number || '').trim().toUpperCase();
            const email = (body.email || '').trim().toLowerCase();
            const department = (body.department || '').trim();
            const phone = (body.phone || '').trim();
            const password = body.password || '';
            const confirmPassword = body.confirm_password || '';

            if (!username || !fullName || !studentIdNumber || !email || !department || !password || !confirmPassword) {
                return buildResponse(400, { success: false, message: 'All required fields must be filled.' });
            }

            const emailRegex = /^[\w\.-]+@[\w\.-]+\.\w+$/;
            if (!emailRegex.test(email)) {
                return buildResponse(400, { success: false, message: 'Invalid email address format.' });
            }

            if (password.length < 6) {
                return buildResponse(400, { success: false, message: 'Password must be at least 6 characters.' });
            }

            if (password !== confirmPassword) {
                return buildResponse(400, { success: false, message: 'Passwords do not match.' });
            }

            // Check uniqueness
            const checkUser = await client.query('SELECT id FROM users WHERE LOWER(username) = LOWER($1) OR LOWER(email) = LOWER($2)', [username, email]);
            if (checkUser.rows.length > 0) {
                return buildResponse(400, { success: false, message: 'Username or email is already registered.' });
            }

            const checkStudent = await client.query('SELECT id FROM students WHERE student_id_number = $1 OR LOWER(email) = LOWER($2)', [studentIdNumber, email]);
            if (checkStudent.rows.length > 0) {
                return buildResponse(400, { success: false, message: `Student ID or email is already registered.` });
            }

            const passHash = hashPassword(password);
            await client.query('BEGIN');
            const insertUserRes = await client.query(
                'INSERT INTO users (username, email, password_hash, role, created_at) VALUES ($1, $2, $3, $4, NOW()) RETURNING id',
                [username, email, passHash, 'student']
            );
            const newUserId = insertUserRes.rows[0].id;

            await client.query(
                'INSERT INTO students (student_id_number, full_name, email, department, phone, registration_date, user_id) VALUES ($1, $2, $3, $4, $5, NOW(), $6)',
                [studentIdNumber, fullName, email, department, phone || null, newUserId]
            );
            await client.query('COMMIT');

            return buildResponse(201, {
                success: true,
                message: 'Registration successful! You can now sign in.'
            });
        }

        // --- 4. AUTH / LOGOUT ---
        if ((path === '/auth/logout' || path === '/logout')) {
            const clearCookie = `session=; Path=/; HttpOnly; SameSite=Lax; Expires=Thu, 01 Jan 1970 00:00:00 GMT`;
            return {
                statusCode: 200,
                headers: {
                    'Content-Type': 'application/json',
                    'Set-Cookie': clearCookie,
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true'
                },
                body: JSON.stringify({ success: true, message: 'Logged out successfully.' })
            };
        }

        // --- 5. STATS ---
        if (path === '/stats' && method === 'GET') {
            const titlesRes = await client.query('SELECT COUNT(*) as count FROM books');
            const copiesRes = await client.query('SELECT COALESCE(SUM(total_copies), 0) as total, COALESCE(SUM(available_copies), 0) as available FROM books');
            const issuedRes = await client.query("SELECT COUNT(*) as count FROM borrow_records WHERE status = 'issued'");
            const studentsRes = await client.query('SELECT COUNT(*) as count FROM students');
            const overdueRes = await client.query("SELECT COUNT(*) as count FROM borrow_records WHERE status = 'issued' AND due_date < CURRENT_DATE");

            return buildResponse(200, {
                total_titles: parseInt(titlesRes.rows[0].count, 10),
                total_copies: parseInt(copiesRes.rows[0].total, 10),
                available_copies: parseInt(copiesRes.rows[0].available, 10),
                currently_issued: parseInt(issuedRes.rows[0].count, 10),
                total_students: parseInt(studentsRes.rows[0].count, 10),
                overdue_count: parseInt(overdueRes.rows[0].count, 10)
            });
        }

        // --- 6. BOOKS ---
        if (path === '/books' && method === 'GET') {
            const q = (queryParams.q || '').trim();
            const available = queryParams.available === 'yes';

            let query = 'SELECT * FROM books WHERE 1=1';
            const params = [];
            if (q) {
                params.push(`%${q}%`);
                query += ` AND (title ILIKE $${params.length} OR author ILIKE $${params.length} OR category ILIKE $${params.length} OR isbn ILIKE $${params.length})`;
            }
            if (available) {
                query += ' AND available_copies > 0';
            }
            query += ' ORDER BY id DESC';

            const res = await client.query(query, params);
            const books = res.rows.map(b => ({
                id: b.id,
                isbn: b.isbn || '',
                title: b.title,
                author: b.author,
                category: b.category,
                publisher: b.publisher || '',
                total_copies: b.total_copies,
                available_copies: b.available_copies,
                issued_copies: Math.max(0, b.total_copies - b.available_copies),
                is_available: b.available_copies > 0,
                date_added: b.date_added ? b.date_added.toISOString().split('T')[0] : ''
            }));
            return buildResponse(200, { books, total: books.length });
        }

        if (path === '/books' && method === 'POST') {
            const title = (body.title || '').trim();
            const author = (body.author || '').trim();
            const category = (body.category || '').trim();
            const isbn = (body.isbn || '').trim();
            const publisher = (body.publisher || '').trim();
            const totalCopies = parseInt(body.total_copies, 10) || 1;
            const availableCopies = body.available_copies !== undefined ? parseInt(body.available_copies, 10) : totalCopies;

            if (!title || !author || !category) {
                return buildResponse(400, { success: false, message: 'Title, Author, and Category are required.' });
            }

            const res = await client.query(
                'INSERT INTO books (title, author, category, isbn, publisher, total_copies, available_copies, date_added) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW()) RETURNING id',
                [title, author, category, isbn || null, publisher || null, totalCopies, availableCopies]
            );
            return buildResponse(201, { success: true, message: 'Book added successfully.', book_id: res.rows[0].id });
        }

        const bookIdMatch = path.match(/^\/books\/(\d+)$/);
        if (bookIdMatch) {
            const bookId = parseInt(bookIdMatch[1], 10);
            if (method === 'PUT') {
                const title = (body.title || '').trim();
                const author = (body.author || '').trim();
                const category = (body.category || '').trim();
                const totalCopies = parseInt(body.total_copies, 10);
                const availableCopies = parseInt(body.available_copies, 10);

                await client.query(
                    'UPDATE books SET title = COALESCE(NULLIF($1, \'\'), title), author = COALESCE(NULLIF($2, \'\'), author), category = COALESCE(NULLIF($3, \'\'), category), total_copies = COALESCE($4, total_copies), available_copies = COALESCE($5, available_copies) WHERE id = $6',
                    [title, author, category, isNaN(totalCopies) ? null : totalCopies, isNaN(availableCopies) ? null : availableCopies, bookId]
                );
                return buildResponse(200, { success: true, message: 'Book updated successfully.' });
            }
            if (method === 'DELETE') {
                await client.query('DELETE FROM books WHERE id = $1', [bookId]);
                return buildResponse(200, { success: true, message: 'Book deleted successfully.' });
            }
        }

        // --- 7. STUDENTS ---
        if (path === '/students' && method === 'GET') {
            const q = (queryParams.q || '').trim();
            let query = 'SELECT s.*, (SELECT COUNT(*) FROM borrow_records r WHERE r.student_id = s.id AND r.status = \'issued\') as active_loans FROM students s WHERE 1=1';
            const params = [];
            if (q) {
                params.push(`%${q}%`);
                query += ` AND (s.full_name ILIKE $${params.length} OR s.student_id_number ILIKE $${params.length} OR s.department ILIKE $${params.length})`;
            }
            query += ' ORDER BY s.id DESC';
            const res = await client.query(query, params);
            const students = res.rows.map(s => ({
                id: s.id,
                student_id_number: s.student_id_number,
                full_name: s.full_name,
                email: s.email,
                department: s.department,
                phone: s.phone || '',
                active_borrows_count: parseInt(s.active_loans, 10) || 0
            }));
            return buildResponse(200, { students, total: students.length });
        }

        // --- 8. CIRCULATION: ISSUE & RETURN ---
        if (path === '/issue' && method === 'POST') {
            const bookId = parseInt(body.book_id, 10);
            const studentId = parseInt(body.student_id, 10);
            const loanDays = parseInt(body.loan_days, 10) || 14;
            const notes = (body.notes || '').trim();

            if (!bookId || !studentId) {
                return buildResponse(400, { success: false, message: 'Book and Student are required.' });
            }

            const bookRes = await client.query('SELECT available_copies FROM books WHERE id = $1', [bookId]);
            if (bookRes.rows.length === 0 || bookRes.rows[0].available_copies < 1) {
                return buildResponse(400, { success: false, message: 'No available copies left for this book.' });
            }

            await client.query('BEGIN');
            await client.query('UPDATE books SET available_copies = available_copies - 1 WHERE id = $1', [bookId]);
            await client.query(
                "INSERT INTO borrow_records (book_id, student_id, issue_date, due_date, status, notes) VALUES ($1, $2, CURRENT_DATE, CURRENT_DATE + ($3 || ' days')::INTERVAL, 'issued', $4)",
                [bookId, studentId, loanDays, notes || null]
            );
            await client.query('COMMIT');
            return buildResponse(201, { success: true, message: 'Book issued successfully.' });
        }

        const returnMatch = path.match(/^\/return\/(\d+)$/);
        if (returnMatch && method === 'POST') {
            const recordId = parseInt(returnMatch[1], 10);
            const recRes = await client.query("SELECT book_id, status FROM borrow_records WHERE id = $1", [recordId]);
            if (recRes.rows.length === 0) {
                return buildResponse(404, { success: false, message: 'Borrow record not found.' });
            }
            if (recRes.rows[0].status === 'returned') {
                return buildResponse(400, { success: false, message: 'Book has already been returned.' });
            }

            const bookId = recRes.rows[0].book_id;
            await client.query('BEGIN');
            await client.query("UPDATE borrow_records SET status = 'returned', return_date = CURRENT_DATE WHERE id = $1", [recordId]);
            await client.query("UPDATE books SET available_copies = available_copies + 1 WHERE id = $1", [bookId]);
            await client.query('COMMIT');
            return buildResponse(200, { success: true, message: 'Book marked as returned successfully.' });
        }

        // --- 9. ISSUED & HISTORY ---
        if (path === '/issued' && method === 'GET') {
            const query = `
                SELECT r.*, b.title as book_title, b.author as book_author, s.full_name as student_name, s.student_id_number, s.department as student_department
                FROM borrow_records r
                JOIN books b ON r.book_id = b.id
                JOIN students s ON r.student_id = s.id
                WHERE r.status = 'issued'
                ORDER BY r.due_date ASC
            `;
            const res = await client.query(query);
            const records = res.rows.map(r => ({
                id: r.id,
                book_id: r.book_id,
                book_title: r.book_title,
                book_author: r.book_author,
                student_id: r.student_id,
                student_name: r.student_name,
                student_id_number: r.student_id_number,
                student_department: r.student_department,
                issue_date: r.issue_date ? r.issue_date.toISOString().split('T')[0] : '',
                due_date: r.due_date ? r.due_date.toISOString().split('T')[0] : '',
                status: r.status,
                is_overdue: r.due_date && new Date(r.due_date) < new Date()
            }));
            return buildResponse(200, { records, total: records.length });
        }

        if (path === '/history' && method === 'GET') {
            const query = `
                SELECT r.*, b.title as book_title, b.author as book_author, s.full_name as student_name, s.student_id_number, s.department as student_department
                FROM borrow_records r
                JOIN books b ON r.book_id = b.id
                JOIN students s ON r.student_id = s.id
                ORDER BY r.id DESC
            `;
            const res = await client.query(query);
            const records = res.rows.map(r => ({
                id: r.id,
                book_id: r.book_id,
                book_title: r.book_title,
                book_author: r.book_author,
                student_id: r.student_id,
                student_name: r.student_name,
                student_id_number: r.student_id_number,
                student_department: r.student_department,
                issue_date: r.issue_date ? r.issue_date.toISOString().split('T')[0] : '',
                due_date: r.due_date ? r.due_date.toISOString().split('T')[0] : '',
                return_date: r.return_date ? r.return_date.toISOString().split('T')[0] : null,
                status: r.status,
                is_overdue: r.status === 'issued' && r.due_date && new Date(r.due_date) < new Date()
            }));
            return buildResponse(200, { records, total: records.length });
        }

        // --- 10. STUDENT DASHBOARD & MY BOOKS ---
        if (path === '/student/dashboard' && method === 'GET') {
            if (!currentUserId) {
                return buildResponse(401, { success: false, message: 'Authentication required.' });
            }
            const stuRes = await client.query('SELECT * FROM students WHERE user_id = $1 LIMIT 1', [currentUserId]);
            if (stuRes.rows.length === 0) {
                return buildResponse(404, { success: false, message: 'Student profile not found.' });
            }
            const student = stuRes.rows[0];

            const myIssuedRes = await client.query(
                "SELECT r.*, b.title as book_title, b.author as book_author, b.category as book_category FROM borrow_records r JOIN books b ON r.book_id = b.id WHERE r.student_id = $1 AND r.status = 'issued' ORDER BY r.due_date ASC",
                [student.id]
            );

            const overdueCount = myIssuedRes.rows.filter(r => r.due_date && new Date(r.due_date) < new Date()).length;

            return buildResponse(200, {
                student,
                current_borrows: myIssuedRes.rows.map(r => ({
                    id: r.id,
                    book_title: r.book_title,
                    book_author: r.book_author,
                    book_category: r.book_category,
                    issue_date: r.issue_date ? r.issue_date.toISOString().split('T')[0] : '',
                    due_date: r.due_date ? r.due_date.toISOString().split('T')[0] : '',
                    is_overdue: r.due_date && new Date(r.due_date) < new Date()
                })),
                active_count: myIssuedRes.rows.length,
                overdue_count: overdueCount
            });
        }

        if (path === '/student/my-books' && method === 'GET') {
            if (!currentUserId) {
                return buildResponse(401, { success: false, message: 'Authentication required.' });
            }
            const stuRes = await client.query('SELECT id FROM students WHERE user_id = $1 LIMIT 1', [currentUserId]);
            if (stuRes.rows.length === 0) {
                return buildResponse(404, { success: false, message: 'Student profile not found.' });
            }
            const studentId = stuRes.rows[0].id;

            const res = await client.query(
                "SELECT r.*, b.title as book_title, b.author as book_author, b.category as book_category FROM borrow_records r JOIN books b ON r.book_id = b.id WHERE r.student_id = $1 AND r.status = 'issued' ORDER BY r.due_date ASC",
                [studentId]
            );
            return buildResponse(200, {
                records: res.rows.map(r => ({
                    id: r.id,
                    book_title: r.book_title,
                    book_author: r.book_author,
                    book_category: r.book_category,
                    issue_date: r.issue_date ? r.issue_date.toISOString().split('T')[0] : '',
                    due_date: r.due_date ? r.due_date.toISOString().split('T')[0] : '',
                    status: r.status,
                    is_overdue: r.due_date && new Date(r.due_date) < new Date()
                }))
            });
        }

        if (path === '/student/history' && method === 'GET') {
            if (!currentUserId) {
                return buildResponse(401, { success: false, message: 'Authentication required.' });
            }
            const stuRes = await client.query('SELECT id FROM students WHERE user_id = $1 LIMIT 1', [currentUserId]);
            if (stuRes.rows.length === 0) {
                return buildResponse(404, { success: false, message: 'Student profile not found.' });
            }
            const studentId = stuRes.rows[0].id;

            const res = await client.query(
                "SELECT r.*, b.title as book_title, b.author as book_author FROM borrow_records r JOIN books b ON r.book_id = b.id WHERE r.student_id = $1 ORDER BY r.id DESC",
                [studentId]
            );
            return buildResponse(200, {
                records: res.rows.map(r => ({
                    id: r.id,
                    book_title: r.book_title,
                    book_author: r.book_author,
                    issue_date: r.issue_date ? r.issue_date.toISOString().split('T')[0] : '',
                    due_date: r.due_date ? r.due_date.toISOString().split('T')[0] : '',
                    return_date: r.return_date ? r.return_date.toISOString().split('T')[0] : null,
                    status: r.status
                }))
            });
        }

        // Endpoint not found in API
        return buildResponse(404, {
            success: false,
            error: 'NOT_FOUND',
            message: `Route not found: ${method} /api${path}`
        });

    } catch (err) {
        console.error('API Error:', err);
        return buildResponse(500, {
            success: false,
            error: 'INTERNAL_SERVER_ERROR',
            message: 'Internal server error processing request.'
        });
    } finally {
        if (client) client.release();
    }
};
