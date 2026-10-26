// Library Management System - Frontend SPA Controller
// Communicates with the Flask Backend via JSON REST APIs

(function () {
    "use strict";

    // Application State
    const state = {
        currentUser: null,
        currentStudent: null,
        currentView: "home",
        stats: null,
        books: [],
        categories: [],
        students: [],
        departments: [],
        issuedRecords: [],
        historyRecords: []
    };

    // Helper: Build API URL
    function apiUrl(path) {
        const base = (window.API_BASE_URL || "").replace(/\/$/, "");
        const cleanPath = path.startsWith("/") ? path : `/${path}`;
        return `${base}${cleanPath}`;
    }

    // Helper: Standard Fetch with Credentials & JSON
    async function apiRequest(endpoint, options = {}) {
        const url = apiUrl(endpoint);
        const defaultOptions = {
            credentials: "include",
            headers: {
                "Accept": "application/json"
            }
        };

        const config = { ...defaultOptions, ...options };
        config.headers = { ...defaultOptions.headers, ...(options.headers || {}) };

        if (config.body && typeof config.body === "object" && !(config.body instanceof FormData)) {
            config.headers["Content-Type"] = "application/json";
            config.body = JSON.stringify(config.body);
        }

        try {
            showColdStartBanner(false);
            const response = await fetch(url, config);

            // If Render is waking up from cold start (HTTP 502/503/504)
            if ([502, 503, 504].includes(response.status)) {
                showColdStartBanner(true);
                throw new Error("Backend server is waking up on Render. Please wait 30-45 seconds and retry.");
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const message = data.message || `Request failed with status ${response.status}`;
                throw new Error(message);
            }

            return data;
        } catch (err) {
            if (err.message && err.message.includes("Failed to fetch")) {
                showColdStartBanner(true);
            }
            throw err;
        }
    }

    // Toast Notifications
    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const toastEl = document.createElement("div");
        toastEl.className = `alert alert-${type} alert-dismissible fade show shadow-sm mb-2`;
        toastEl.role = "alert";
        toastEl.innerHTML = `
            <span>${escapeHtml(message)}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        container.appendChild(toastEl);

        setTimeout(() => {
            toastEl.classList.remove("show");
            setTimeout(() => toastEl.remove(), 250);
        }, 5000);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str).replace(/[&<>"']/g, function (m) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
        });
    }

    function showColdStartBanner(show) {
        const banner = document.getElementById("coldStartBanner");
        if (banner) {
            banner.style.display = show ? "block" : "none";
        }
    }

    // Router / View Switcher
    function navigateTo(viewName, params = {}) {
        state.currentView = viewName;
        window.location.hash = viewName;

        // Hide all views
        document.querySelectorAll(".view-section").forEach(sec => sec.style.display = "none");

        // Show target view
        const target = document.getElementById(`view-${viewName}`);
        if (target) {
            target.style.display = "block";
            window.scrollTo({ top: 0, behavior: "smooth" });
        } else {
            console.warn(`View view-${viewName} not found, defaulting to home`);
            const home = document.getElementById("view-home");
            if (home) home.style.display = "block";
        }

        updateNavActive(viewName);

        // Load View Data
        switch (viewName) {
            case "home":
                loadHomeData();
                break;
            case "admin-dashboard":
                loadAdminDashboard();
                break;
            case "admin-books":
                loadAdminBooks();
                break;
            case "admin-students":
                loadAdminStudents();
                break;
            case "admin-issue":
                loadAdminIssueForm(params);
                break;
            case "admin-issued":
                loadAdminIssued();
                break;
            case "admin-history":
                loadAdminHistory();
                break;
            case "student-dashboard":
                loadStudentDashboard();
                break;
            case "student-catalog":
                loadStudentCatalog();
                break;
            case "student-my-books":
                loadStudentMyBooks();
                break;
            case "student-history":
                loadStudentHistory();
                break;
        }
    }

    function updateNavActive(viewName) {
        document.querySelectorAll(".nav-link").forEach(link => {
            const href = link.getAttribute("href") || "";
            if (href === `#${viewName}`) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });
    }

    // Check Current Authentication State
    async function checkAuth() {
        try {
            const data = await apiRequest("/api/auth/me");
            if (data.authenticated && data.user) {
                state.currentUser = data.user;
                state.currentStudent = data.student || null;
            } else {
                state.currentUser = null;
                state.currentStudent = null;
            }
        } catch {
            state.currentUser = null;
            state.currentStudent = null;
        }
        updateAuthNav();
    }

    function updateAuthNav() {
        const guestNav = document.getElementById("guestNav");
        const userNav = document.getElementById("userNav");
        const adminLinks = document.getElementById("adminNavLinks");
        const studentLinks = document.getElementById("studentNavLinks");
        const userNameSpan = document.getElementById("navUserName");
        const userRoleBadge = document.getElementById("navUserRole");

        if (state.currentUser) {
            if (guestNav) guestNav.style.display = "none";
            if (userNav) userNav.style.display = "flex";
            if (userNameSpan) userNameSpan.textContent = state.currentUser.username;
            if (userRoleBadge) {
                userRoleBadge.textContent = state.currentUser.role;
                userRoleBadge.className = `badge ${state.currentUser.role === "admin" ? "bg-warning text-dark" : "bg-info text-dark"} me-1 text-uppercase`;
            }

            if (state.currentUser.role === "admin") {
                if (adminLinks) adminLinks.style.display = "flex";
                if (studentLinks) studentLinks.style.display = "none";
            } else {
                if (adminLinks) adminLinks.style.display = "none";
                if (studentLinks) studentLinks.style.display = "flex";
            }
        } else {
            if (guestNav) guestNav.style.display = "flex";
            if (userNav) userNav.style.display = "none";
            if (adminLinks) adminLinks.style.display = "none";
            if (studentLinks) studentLinks.style.display = "none";
        }
    }

    // View: Home
    async function loadHomeData() {
        try {
            const stats = await apiRequest("/api/stats");
            state.stats = stats;
            document.getElementById("homeStatTitles").textContent = stats.total_titles || 0;
            document.getElementById("homeStatCopies").textContent = stats.total_copies || 0;
            document.getElementById("homeStatAvailable").textContent = stats.available_copies || 0;
            document.getElementById("homeStatStudents").textContent = stats.total_students || 0;
        } catch (e) {
            console.error("Failed to load stats", e);
        }

        try {
            const booksData = await apiRequest("/api/books");
            const featuredList = document.getElementById("homeFeaturedBooks");
            if (!featuredList) return;

            const featured = (booksData.books || []).slice(0, 6);
            if (featured.length === 0) {
                featuredList.innerHTML = `<div class="col-12 text-center py-4 text-muted"><p>No books added to catalog yet.</p></div>`;
                return;
            }

            featuredList.innerHTML = featured.map(b => `
                <div class="col-md-4">
                    <div class="card h-100 border shadow-sm">
                        <div class="card-body">
                            <span class="badge bg-secondary mb-2">${escapeHtml(b.category)}</span>
                            <h6 class="card-title fw-bold text-truncate" title="${escapeHtml(b.title)}">${escapeHtml(b.title)}</h6>
                            <p class="card-text text-muted small mb-2"><i class="bi bi-pen"></i> ${escapeHtml(b.author)}</p>
                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <small class="text-muted">Copies: ${b.available_copies}/${b.total_copies}</small>
                                ${b.available_copies > 0
                                    ? `<span class="badge badge-available">Available</span>`
                                    : `<span class="badge badge-unavailable">Out of Stock</span>`}
                            </div>
                        </div>
                    </div>
                </div>
            `).join("");
        } catch (e) {
            console.error("Failed to load featured books", e);
        }
    }

    // View: Admin Dashboard
    async function loadAdminDashboard() {
        if (!state.currentUser || state.currentUser.role !== "admin") {
            showToast("Administrator access required.", "danger");
            navigateTo("login");
            return;
        }

        try {
            const stats = await apiRequest("/api/stats");
            document.getElementById("admTotalCopies").textContent = stats.total_copies || 0;
            document.getElementById("admTotalTitles").textContent = `${stats.total_titles || 0} unique titles`;
            document.getElementById("admAvailableCopies").textContent = stats.available_copies || 0;
            document.getElementById("admCurrentlyIssued").textContent = stats.currently_issued || 0;
            document.getElementById("admOverdueCount").textContent = stats.overdue_count || 0;
        } catch (e) {
            showToast("Failed to load dashboard metrics.", "danger");
        }

        try {
            const historyData = await apiRequest("/api/history");
            const recent = (historyData.records || []).slice(0, 8);
            const tbody = document.getElementById("admRecentBorrowsTbody");

            if (!tbody) return;

            if (recent.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No circulation activity found.</td></tr>`;
            } else {
                tbody.innerHTML = recent.map(r => `
                    <tr>
                        <td class="fw-semibold text-truncate" style="max-width:200px;">${escapeHtml(r.book_title)}</td>
                        <td>
                            <div>${escapeHtml(r.student_name)}</div>
                            <small class="text-muted">${escapeHtml(r.student_id_number)}</small>
                        </td>
                        <td>${escapeHtml(r.issue_date)}</td>
                        <td>
                            ${escapeHtml(r.due_date)}
                            ${r.is_overdue ? `<span class="badge bg-danger ms-1">Overdue</span>` : ""}
                        </td>
                        <td>
                            ${r.status === "issued"
                                ? `<span class="badge bg-warning text-dark">Issued</span>`
                                : `<span class="badge bg-success">Returned</span>`}
                        </td>
                        <td>
                            ${r.status === "issued"
                                ? `<button class="btn btn-sm btn-outline-success btn-return-action" data-id="${r.id}"><i class="bi bi-check2"></i> Return</button>`
                                : `<span class="text-muted small"><i class="bi bi-check-all text-success"></i> Done</span>`}
                        </td>
                    </tr>
                `).join("");
            }

            // Overdue Alert Sidebar
            const overdue = (historyData.records || []).filter(r => r.status === "issued" && r.is_overdue).slice(0, 5);
            const overdueList = document.getElementById("admOverdueList");
            if (overdueList) {
                if (overdue.length === 0) {
                    overdueList.innerHTML = `<div class="text-center py-4 text-muted"><i class="bi bi-check-circle-fill text-success fs-1 d-block mb-2"></i>No overdue books!</div>`;
                } else {
                    overdueList.innerHTML = overdue.map(o => `
                        <div class="list-group-item px-0 py-2 border-0 border-bottom">
                            <div class="d-flex justify-content-between">
                                <strong class="text-truncate" style="max-width:160px;">${escapeHtml(o.book_title)}</strong>
                                <span class="badge bg-danger">${o.days_overdue}d late</span>
                            </div>
                            <small class="text-muted">${escapeHtml(o.student_name)} (${escapeHtml(o.student_id_number)})</small>
                            <div class="mt-1 d-flex justify-content-between align-items-center">
                                <small class="text-secondary">Due: ${o.due_date}</small>
                                <button class="btn btn-xs btn-outline-success btn-sm btn-return-action" data-id="${o.id}">Return</button>
                            </div>
                        </div>
                    `).join("");
                }
            }
        } catch (e) {
            console.error("Failed to load recent activity", e);
        }
    }

    // View: Admin Book Management
    async function loadAdminBooks() {
        const queryStr = (document.getElementById("admBookSearchInput")?.value || "").trim();
        const catFilter = document.getElementById("admBookCatFilter")?.value || "";

        let endpoint = `/api/books?q=${encodeURIComponent(queryStr)}`;
        if (catFilter) endpoint += `&category=${encodeURIComponent(catFilter)}`;

        try {
            const data = await apiRequest(endpoint);
            state.books = data.books || [];
            state.categories = data.categories || [];

            // Populate category dropdown
            const catSelect = document.getElementById("admBookCatFilter");
            if (catSelect && catSelect.options.length <= 1) {
                state.categories.forEach(c => {
                    const opt = document.createElement("option");
                    opt.value = c;
                    opt.textContent = c;
                    catSelect.appendChild(opt);
                });
            }

            const tbody = document.getElementById("admBooksTbody");
            if (!tbody) return;

            if (state.books.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No books found matching criteria.</td></tr>`;
                return;
            }

            tbody.innerHTML = state.books.map(b => `
                <tr>
                    <td class="text-muted fw-bold">#${b.id}</td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(b.title)}</div>
                        <small class="text-muted"><i class="bi bi-pen"></i> ${escapeHtml(b.author)}</small>
                    </td>
                    <td><span class="badge bg-secondary-subtle text-secondary border">${escapeHtml(b.category)}</span></td>
                    <td><code>${escapeHtml(b.isbn || "-")}</code></td>
                    <td><span class="badge bg-dark">${b.total_copies}</span></td>
                    <td>
                        ${b.available_copies > 0
                            ? `<span class="badge badge-available">${b.available_copies} in stock</span>`
                            : `<span class="badge badge-unavailable">0 available</span>`}
                    </td>
                    <td><span class="badge bg-light text-dark border">${b.issued_copies}</span></td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm">
                            ${b.available_copies > 0 ? `<button class="btn btn-outline-success btn-quick-issue" data-id="${b.id}" title="Issue book"><i class="bi bi-arrow-up-right-circle"></i></button>` : ""}
                            <button class="btn btn-outline-primary btn-edit-book" data-id="${b.id}" title="Edit book"><i class="bi bi-pencil"></i></button>
                            <button class="btn btn-outline-danger btn-delete-book" data-id="${b.id}" data-title="${escapeHtml(b.title)}" title="Delete book"><i class="bi bi-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load books: " + e.message, "danger");
        }
    }

    // View: Admin Students Management
    async function loadAdminStudents() {
        const queryStr = (document.getElementById("admStudentSearchInput")?.value || "").trim();
        const deptFilter = document.getElementById("admStudentDeptFilter")?.value || "";

        let endpoint = `/api/students?q=${encodeURIComponent(queryStr)}`;
        if (deptFilter) endpoint += `&department=${encodeURIComponent(deptFilter)}`;

        try {
            const data = await apiRequest(endpoint);
            state.students = data.students || [];
            state.departments = data.departments || [];

            const deptSelect = document.getElementById("admStudentDeptFilter");
            if (deptSelect && deptSelect.options.length <= 1) {
                state.departments.forEach(d => {
                    const opt = document.createElement("option");
                    opt.value = d;
                    opt.textContent = d;
                    deptSelect.appendChild(opt);
                });
            }

            const tbody = document.getElementById("admStudentsTbody");
            if (!tbody) return;

            if (state.students.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No student records found.</td></tr>`;
                return;
            }

            tbody.innerHTML = state.students.map(s => `
                <tr>
                    <td><span class="badge bg-dark-subtle text-dark border fw-bold">${escapeHtml(s.student_id_number)}</span></td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(s.full_name)}</div>
                        <small class="text-muted"><a href="mailto:${escapeHtml(s.email)}" class="text-decoration-none text-muted">${escapeHtml(s.email)}</a></small>
                    </td>
                    <td><span class="badge bg-light text-dark border">${escapeHtml(s.department)}</span></td>
                    <td><small class="text-muted">${escapeHtml(s.phone || "-")}</small></td>
                    <td>
                        ${s.active_borrows_count > 0
                            ? `<span class="badge bg-warning text-dark">${s.active_borrows_count} active</span>`
                            : `<span class="badge bg-light text-muted border">None</span>`}
                    </td>
                    <td><small class="text-muted">${escapeHtml(s.registration_date)}</small></td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-success btn-quick-issue-student" data-id="${s.id}" title="Issue book to student"><i class="bi bi-plus-circle"></i></button>
                            <button class="btn btn-outline-primary btn-edit-student" data-id="${s.id}" title="Edit student"><i class="bi bi-pencil"></i></button>
                            <button class="btn btn-outline-danger btn-delete-student" data-id="${s.id}" data-name="${escapeHtml(s.full_name)}" title="Delete student"><i class="bi bi-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load students: " + e.message, "danger");
        }
    }

    // View: Admin Issue Form
    async function loadAdminIssueForm(params = {}) {
        try {
            const [booksData, studentsData] = await Promise.all([
                apiRequest("/api/books?available=yes"),
                apiRequest("/api/students")
            ]);

            const bookSelect = document.getElementById("issueBookSelect");
            const studentSelect = document.getElementById("issueStudentSelect");
            const dueDateInput = document.getElementById("issueDueDate");

            // Default due date: 14 days from today
            if (dueDateInput) {
                const due = new Date();
                due.setDate(due.getDate() + 14);
                dueDateInput.value = due.toISOString().split("T")[0];
                dueDateInput.min = new Date().toISOString().split("T")[0];
            }

            if (bookSelect) {
                bookSelect.innerHTML = `<option value="" disabled selected>Choose available book...</option>` +
                    (booksData.books || []).map(b => `
                        <option value="${b.id}" ${params.bookId == b.id ? "selected" : ""}>
                            ${escapeHtml(b.title)} by ${escapeHtml(b.author)} (Stock: ${b.available_copies}/${b.total_copies})
                        </option>
                    `).join("");
            }

            if (studentSelect) {
                studentSelect.innerHTML = `<option value="" disabled selected>Choose registered student...</option>` +
                    (studentsData.students || []).map(s => `
                        <option value="${s.id}" ${params.studentId == s.id ? "selected" : ""}>
                            ${escapeHtml(s.full_name)} (${escapeHtml(s.student_id_number)} - ${escapeHtml(s.department)})
                        </option>
                    `).join("");
            }
        } catch (e) {
            showToast("Failed to load issue form data: " + e.message, "danger");
        }
    }

    // View: Admin Active Issued Books
    async function loadAdminIssued() {
        const queryStr = (document.getElementById("admIssuedSearchInput")?.value || "").trim();
        const filterStatus = document.getElementById("admIssuedFilter")?.value || "all";

        let endpoint = `/api/issued?q=${encodeURIComponent(queryStr)}&filter=${encodeURIComponent(filterStatus)}`;
        try {
            const data = await apiRequest(endpoint);
            state.issuedRecords = data.records || [];

            const tbody = document.getElementById("admIssuedTbody");
            if (!tbody) return;

            if (state.issuedRecords.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No currently issued books found.</td></tr>`;
                return;
            }

            tbody.innerHTML = state.issuedRecords.map(r => `
                <tr class="${r.is_overdue ? "table-danger-subtle" : ""}">
                    <td>
                        <div class="fw-semibold">${escapeHtml(r.book_title)}</div>
                        <small class="text-muted"><i class="bi bi-pen"></i> ${escapeHtml(r.book_author)} &middot; ${escapeHtml(r.book_category)}</small>
                    </td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(r.student_name)}</div>
                        <small class="text-muted">${escapeHtml(r.student_id_number)} &middot; ${escapeHtml(r.student_department)}</small>
                    </td>
                    <td>${escapeHtml(r.issue_date)}</td>
                    <td><span class="fw-semibold">${escapeHtml(r.due_date)}</span></td>
                    <td>
                        ${r.is_overdue
                            ? `<span class="badge bg-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i> Overdue (${r.days_overdue} days)</span>`
                            : r.days_left === 0
                                ? `<span class="badge bg-warning text-dark">Due Today</span>`
                                : `<span class="badge bg-success-subtle text-success border border-success">${r.days_left} days remaining</span>`}
                    </td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-success fw-semibold btn-return-action" data-id="${r.id}">
                            <i class="bi bi-check2-circle me-1"></i> Record Return
                        </button>
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load active loans: " + e.message, "danger");
        }
    }

    // View: Admin Circulation History
    async function loadAdminHistory() {
        const queryStr = (document.getElementById("admHistorySearchInput")?.value || "").trim();
        const status = document.getElementById("admHistoryStatusFilter")?.value || "";

        let endpoint = `/api/history?q=${encodeURIComponent(queryStr)}&status=${encodeURIComponent(status)}`;
        try {
            const data = await apiRequest(endpoint);
            state.historyRecords = data.records || [];

            const tbody = document.getElementById("admHistoryTbody");
            if (!tbody) return;

            if (state.historyRecords.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No historical records found.</td></tr>`;
                return;
            }

            tbody.innerHTML = state.historyRecords.map(r => `
                <tr>
                    <td class="text-muted">#${r.id}</td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(r.book_title)}</div>
                        <small class="text-muted">${escapeHtml(r.book_author)}</small>
                    </td>
                    <td>
                        <div>${escapeHtml(r.student_name)}</div>
                        <small class="text-muted">${escapeHtml(r.student_id_number)}</small>
                    </td>
                    <td>${escapeHtml(r.issue_date)}</td>
                    <td>${escapeHtml(r.due_date)}</td>
                    <td>
                        ${r.return_date
                            ? `<span class="text-success"><i class="bi bi-check-circle me-1"></i> ${escapeHtml(r.return_date)}</span>`
                            : `<span class="text-muted">-</span>`}
                    </td>
                    <td>
                        ${r.status === "returned"
                            ? `<span class="badge bg-success">Returned</span>`
                            : r.is_overdue
                                ? `<span class="badge bg-danger">Overdue (${r.days_overdue}d)</span>`
                                : `<span class="badge bg-warning text-dark">Issued</span>`}
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load history: " + e.message, "danger");
        }
    }

    // View: Student Dashboard
    async function loadStudentDashboard() {
        if (!state.currentUser || state.currentUser.role !== "student") {
            showToast("Student account required.", "danger");
            navigateTo("login");
            return;
        }

        try {
            const data = await apiRequest("/api/student/dashboard");
            document.getElementById("stuWelcomeName").textContent = data.student?.full_name || state.currentUser.username;
            document.getElementById("stuBannerId").textContent = data.student?.student_id_number || "";
            document.getElementById("stuBannerDept").textContent = data.student?.department || "";

            document.getElementById("stuActiveCount").textContent = (data.active_borrows || []).length;
            document.getElementById("stuOverdueCount").textContent = data.overdue_count || 0;
            document.getElementById("stuTotalBorrowed").textContent = data.total_borrowed || 0;

            const tbody = document.getElementById("stuActiveBorrowsTbody");
            if (tbody) {
                if ((data.active_borrows || []).length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">No books currently issued to you.</td></tr>`;
                } else {
                    tbody.innerHTML = data.active_borrows.map(b => `
                        <tr class="${b.is_overdue ? "table-danger-subtle" : ""}">
                            <td>
                                <div class="fw-semibold">${escapeHtml(b.book_title)}</div>
                                <small class="text-muted">${escapeHtml(b.book_author)}</small>
                            </td>
                            <td>${escapeHtml(b.issue_date)}</td>
                            <td>${escapeHtml(b.due_date)}</td>
                            <td>
                                ${b.is_overdue
                                    ? `<span class="badge bg-danger">${b.days_overdue} days overdue</span>`
                                    : `<span class="badge bg-success-subtle text-success border border-success">${b.days_left} days left</span>`}
                            </td>
                        </tr>
                    `).join("");
                }
            }

            const recUl = document.getElementById("stuRecentHistoryList");
            if (recUl) {
                if ((data.recent_history || []).length === 0) {
                    recUl.innerHTML = `<li class="list-group-item text-center py-3 text-muted">No past loans yet.</li>`;
                } else {
                    recUl.innerHTML = data.recent_history.map(r => `
                        <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                            <div>
                                <div class="fw-semibold text-truncate" style="max-width:200px;">${escapeHtml(r.book_title)}</div>
                                <small class="text-muted">Issued: ${r.issue_date}</small>
                            </div>
                            <span class="badge ${r.status === "returned" ? "bg-success" : "bg-warning text-dark"}">${escapeHtml(r.status)}</span>
                        </li>
                    `).join("");
                }
            }
        } catch (e) {
            showToast("Failed to load student dashboard: " + e.message, "danger");
        }
    }

    // View: Student Catalog
    async function loadStudentCatalog() {
        const queryStr = (document.getElementById("stuCatSearchInput")?.value || "").trim();
        const catFilter = document.getElementById("stuCatFilter")?.value || "";
        const availFilter = document.getElementById("stuCatAvailFilter")?.value || "";

        let endpoint = `/api/books?q=${encodeURIComponent(queryStr)}`;
        if (catFilter) endpoint += `&category=${encodeURIComponent(catFilter)}`;
        if (availFilter) endpoint += `&available=${encodeURIComponent(availFilter)}`;

        try {
            const data = await apiRequest(endpoint);
            const container = document.getElementById("stuCatalogGrid");
            if (!container) return;

            // Categories
            const catSelect = document.getElementById("stuCatFilter");
            if (catSelect && catSelect.options.length <= 1 && data.categories) {
                data.categories.forEach(c => {
                    const opt = document.createElement("option");
                    opt.value = c;
                    opt.textContent = c;
                    catSelect.appendChild(opt);
                });
            }

            if ((data.books || []).length === 0) {
                container.innerHTML = `<div class="col-12 text-center py-5 text-muted"><i class="bi bi-journal-x fs-1 d-block mb-2"></i><h5>No books found matching search.</h5></div>`;
                return;
            }

            container.innerHTML = data.books.map(b => `
                <div class="col-md-4 mb-3">
                    <div class="card h-100 border shadow-sm">
                        <div class="card-body d-flex flex-column">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge bg-secondary-subtle text-secondary border">${escapeHtml(b.category)}</span>
                                ${b.available_copies > 0
                                    ? `<span class="badge badge-available"><i class="bi bi-check-circle-fill me-1"></i> Available (${b.available_copies}/${b.total_copies})</span>`
                                    : `<span class="badge badge-unavailable"><i class="bi bi-x-circle-fill me-1"></i> Checked Out</span>`}
                            </div>
                            <h5 class="card-title fw-bold mb-1">${escapeHtml(b.title)}</h5>
                            <p class="text-muted small mb-2"><i class="bi bi-pen me-1"></i> ${escapeHtml(b.author)}</p>
                            ${b.publisher ? `<p class="text-muted small mb-2"><i class="bi bi-building me-1"></i> ${escapeHtml(b.publisher)}</p>` : ""}
                            <div class="mt-auto pt-3 border-top d-flex justify-content-between align-items-center">
                                <small class="text-muted">ISBN: ${escapeHtml(b.isbn || "N/A")}</small>
                                <span class="badge ${b.available_copies > 0 ? "bg-success-subtle text-success" : "bg-warning-subtle text-warning"}">
                                    ${b.available_copies > 0 ? "In Library" : "All Copies Issued"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join("");
        } catch (e) {
            showToast("Failed to load catalog: " + e.message, "danger");
        }
    }

    // View: Student My Books
    async function loadStudentMyBooks() {
        if (!state.currentUser || state.currentUser.role !== "student") return;

        try {
            const data = await apiRequest("/api/student/my-books");
            const tbody = document.getElementById("stuMyBooksTbody");
            if (!tbody) return;

            if ((data.records || []).length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">You do not have any active loans.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.records.map(r => `
                <tr class="${r.is_overdue ? "table-danger-subtle" : ""}">
                    <td>
                        <div class="fw-semibold">${escapeHtml(r.book_title)}</div>
                        <small class="text-muted">${escapeHtml(r.book_author)}</small>
                    </td>
                    <td><span class="badge bg-light text-dark border">${escapeHtml(r.book_category)}</span></td>
                    <td>${escapeHtml(r.issue_date)}</td>
                    <td><span class="fw-semibold">${escapeHtml(r.due_date)}</span></td>
                    <td>
                        ${r.is_overdue
                            ? `<span class="badge bg-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i> Overdue by ${r.days_overdue} days</span>`
                            : `<span class="badge bg-success-subtle text-success border border-success">${r.days_left} days left</span>`}
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load your books: " + e.message, "danger");
        }
    }

    // View: Student History
    async function loadStudentHistory() {
        if (!state.currentUser || state.currentUser.role !== "student") return;

        try {
            const data = await apiRequest("/api/student/history");
            const tbody = document.getElementById("stuHistoryTbody");
            if (!tbody) return;

            if ((data.records || []).length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No borrowing history on record.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.records.map(r => `
                <tr>
                    <td class="fw-semibold">${escapeHtml(r.book_title)}</td>
                    <td class="text-muted">${escapeHtml(r.book_author)}</td>
                    <td>${escapeHtml(r.issue_date)}</td>
                    <td>${escapeHtml(r.due_date)}</td>
                    <td>
                        ${r.return_date
                            ? `<span class="text-success"><i class="bi bi-check-circle me-1"></i> ${escapeHtml(r.return_date)}</span>`
                            : `<span class="text-muted">Active</span>`}
                    </td>
                    <td>
                        ${r.status === "returned"
                            ? `<span class="badge bg-success">Returned</span>`
                            : r.is_overdue
                                ? `<span class="badge bg-danger">Overdue</span>`
                                : `<span class="badge bg-warning text-dark">Issued</span>`}
                    </td>
                </tr>
            `).join("");
        } catch (e) {
            showToast("Failed to load your history: " + e.message, "danger");
        }
    }

    // Event Handlers Setup
    function setupEventListeners() {
        // Navigation clicks
        window.addEventListener("hashchange", () => {
            const hash = window.location.hash.replace("#", "") || "home";
            navigateTo(hash);
        });

        document.querySelectorAll("[data-navigate]").forEach(btn => {
            btn.addEventListener("click", e => {
                e.preventDefault();
                const target = btn.getAttribute("data-navigate");
                navigateTo(target);
            });
        });

        // Logout
        const logoutBtn = document.getElementById("btnLogout");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", async e => {
                e.preventDefault();
                try {
                    await apiRequest("/api/auth/logout", { method: "POST" });
                    state.currentUser = null;
                    state.currentStudent = null;
                    updateAuthNav();
                    showToast("You have been securely logged out.", "info");
                    navigateTo("home");
                } catch (err) {
                    showToast("Logout failed: " + err.message, "danger");
                }
            });
        }

        // Login Form Submit
        const loginForm = document.getElementById("formLogin");
        if (loginForm) {
            loginForm.addEventListener("submit", async e => {
                e.preventDefault();
                const identifier = document.getElementById("loginIdentifier").value.trim();
                const password = document.getElementById("loginPassword").value;

                try {
                    const data = await apiRequest("/api/auth/login", {
                        method: "POST",
                        body: { identifier, password }
                    });

                    state.currentUser = data.user;
                    state.currentStudent = data.student || null;
                    updateAuthNav();
                    showToast(`Welcome back, ${data.user.username}!`, "success");

                    loginForm.reset();
                    if (data.user.role === "admin") {
                        navigateTo("admin-dashboard");
                    } else {
                        navigateTo("student-dashboard");
                    }
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Register Form Submit
        const registerForm = document.getElementById("formRegister");
        if (registerForm) {
            registerForm.addEventListener("submit", async e => {
                e.preventDefault();
                const payload = {
                    username: document.getElementById("regUsername").value.trim(),
                    student_id_number: document.getElementById("regStudentId").value.trim().toUpperCase(),
                    full_name: document.getElementById("regFullName").value.trim(),
                    email: document.getElementById("regEmail").value.trim().toLowerCase(),
                    phone: document.getElementById("regPhone").value.trim(),
                    department: document.getElementById("regDepartment").value,
                    password: document.getElementById("regPassword").value,
                    confirm_password: document.getElementById("regConfirmPassword").value
                };

                try {
                    const res = await apiRequest("/api/auth/register", {
                        method: "POST",
                        body: payload
                    });
                    showToast(res.message || "Registration successful! You can now sign in.", "success");
                    registerForm.reset();
                    navigateTo("login");
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Search inputs with debounce
        let searchTimeout;
        const debounce = (fn, delay = 350) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(fn, delay);
        };

        document.getElementById("admBookSearchInput")?.addEventListener("input", () => debounce(loadAdminBooks));
        document.getElementById("admBookCatFilter")?.addEventListener("change", loadAdminBooks);
        document.getElementById("admStudentSearchInput")?.addEventListener("input", () => debounce(loadAdminStudents));
        document.getElementById("admStudentDeptFilter")?.addEventListener("change", loadAdminStudents);
        document.getElementById("admIssuedSearchInput")?.addEventListener("input", () => debounce(loadAdminIssued));
        document.getElementById("admIssuedFilter")?.addEventListener("change", loadAdminIssued);
        document.getElementById("admHistorySearchInput")?.addEventListener("input", () => debounce(loadAdminHistory));
        document.getElementById("admHistoryStatusFilter")?.addEventListener("change", loadAdminHistory);
        document.getElementById("stuCatSearchInput")?.addEventListener("input", () => debounce(loadStudentCatalog));
        document.getElementById("stuCatFilter")?.addEventListener("change", loadStudentCatalog);
        document.getElementById("stuCatAvailFilter")?.addEventListener("change", loadStudentCatalog);

        // Dynamic delegation for Return actions
        document.body.addEventListener("click", async e => {
            const returnBtn = e.target.closest(".btn-return-action");
            if (returnBtn) {
                const id = returnBtn.getAttribute("data-id");
                if (confirm("Confirm return for this book loan?")) {
                    try {
                        const res = await apiRequest(`/api/return/${id}`, { method: "POST" });
                        showToast(res.message, "success");
                        if (state.currentView === "admin-dashboard") loadAdminDashboard();
                        if (state.currentView === "admin-issued") loadAdminIssued();
                    } catch (err) {
                        showToast(err.message, "danger");
                    }
                }
                return;
            }

            // Quick issue button
            const quickIssueBtn = e.target.closest(".btn-quick-issue");
            if (quickIssueBtn) {
                const bookId = quickIssueBtn.getAttribute("data-id");
                navigateTo("admin-issue", { bookId });
                return;
            }

            const quickIssueStudentBtn = e.target.closest(".btn-quick-issue-student");
            if (quickIssueStudentBtn) {
                const studentId = quickIssueStudentBtn.getAttribute("data-id");
                navigateTo("admin-issue", { studentId });
                return;
            }

            // Delete book
            const deleteBookBtn = e.target.closest(".btn-delete-book");
            if (deleteBookBtn) {
                const id = deleteBookBtn.getAttribute("data-id");
                const title = deleteBookBtn.getAttribute("data-title");
                if (confirm(`Are you sure you want to delete book '${title}'? This cannot be undone.`)) {
                    try {
                        const res = await apiRequest(`/api/books/${id}`, { method: "DELETE" });
                        showToast(res.message, "success");
                        loadAdminBooks();
                    } catch (err) {
                        showToast(err.message, "danger");
                    }
                }
                return;
            }

            // Edit book
            const editBookBtn = e.target.closest(".btn-edit-book");
            if (editBookBtn) {
                const id = editBookBtn.getAttribute("data-id");
                const book = state.books.find(b => b.id == id);
                if (book) {
                    openEditBookModal(book);
                }
                return;
            }

            // Delete student
            const deleteStudentBtn = e.target.closest(".btn-delete-student");
            if (deleteStudentBtn) {
                const id = deleteStudentBtn.getAttribute("data-id");
                const name = deleteStudentBtn.getAttribute("data-name");
                if (confirm(`Are you sure you want to delete student '${name}'?`)) {
                    try {
                        const res = await apiRequest(`/api/students/${id}`, { method: "DELETE" });
                        showToast(res.message, "success");
                        loadAdminStudents();
                    } catch (err) {
                        showToast(err.message, "danger");
                    }
                }
                return;
            }

            // Edit student
            const editStudentBtn = e.target.closest(".btn-edit-student");
            if (editStudentBtn) {
                const id = editStudentBtn.getAttribute("data-id");
                const student = state.students.find(s => s.id == id);
                if (student) {
                    openEditStudentModal(student);
                }
                return;
            }
        });

        // Add Book Form Submit
        const formAddBook = document.getElementById("formAddBook");
        if (formAddBook) {
            formAddBook.addEventListener("submit", async e => {
                e.preventDefault();
                const payload = {
                    title: document.getElementById("addBookTitle").value.trim(),
                    author: document.getElementById("addBookAuthor").value.trim(),
                    category: document.getElementById("addBookCategory").value.trim(),
                    isbn: document.getElementById("addBookIsbn").value.trim(),
                    publisher: document.getElementById("addBookPublisher").value.trim(),
                    total_copies: parseInt(document.getElementById("addBookTotalCopies").value, 10) || 1
                };

                try {
                    const res = await apiRequest("/api/books", { method: "POST", body: payload });
                    showToast(res.message, "success");
                    formAddBook.reset();
                    bootstrap.Modal.getInstance(document.getElementById("modalAddBook"))?.hide();
                    loadAdminBooks();
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Edit Book Form Submit
        const formEditBook = document.getElementById("formEditBook");
        if (formEditBook) {
            formEditBook.addEventListener("submit", async e => {
                e.preventDefault();
                const bookId = document.getElementById("editBookId").value;
                const payload = {
                    title: document.getElementById("editBookTitle").value.trim(),
                    author: document.getElementById("editBookAuthor").value.trim(),
                    category: document.getElementById("editBookCategory").value.trim(),
                    isbn: document.getElementById("editBookIsbn").value.trim(),
                    publisher: document.getElementById("editBookPublisher").value.trim(),
                    total_copies: parseInt(document.getElementById("editBookTotalCopies").value, 10),
                    available_copies: parseInt(document.getElementById("editBookAvailableCopies").value, 10)
                };

                try {
                    const res = await apiRequest(`/api/books/${bookId}`, { method: "PUT", body: payload });
                    showToast(res.message, "success");
                    bootstrap.Modal.getInstance(document.getElementById("modalEditBook"))?.hide();
                    loadAdminBooks();
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Add Student Form Submit
        const formAddStudent = document.getElementById("formAddStudent");
        if (formAddStudent) {
            formAddStudent.addEventListener("submit", async e => {
                e.preventDefault();
                const payload = {
                    full_name: document.getElementById("addStudentName").value.trim(),
                    student_id_number: document.getElementById("addStudentIdNum").value.trim().toUpperCase(),
                    email: document.getElementById("addStudentEmail").value.trim().toLowerCase(),
                    phone: document.getElementById("addStudentPhone").value.trim(),
                    department: document.getElementById("addStudentDepartment").value
                };

                try {
                    const res = await apiRequest("/api/students", { method: "POST", body: payload });
                    showToast(res.message, "success");
                    formAddStudent.reset();
                    bootstrap.Modal.getInstance(document.getElementById("modalAddStudent"))?.hide();
                    loadAdminStudents();
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Edit Student Form Submit
        const formEditStudent = document.getElementById("formEditStudent");
        if (formEditStudent) {
            formEditStudent.addEventListener("submit", async e => {
                e.preventDefault();
                const studentId = document.getElementById("editStudentId").value;
                const payload = {
                    full_name: document.getElementById("editStudentName").value.trim(),
                    email: document.getElementById("editStudentEmail").value.trim().toLowerCase(),
                    phone: document.getElementById("editStudentPhone").value.trim(),
                    department: document.getElementById("editStudentDepartment").value
                };

                try {
                    const res = await apiRequest(`/api/students/${studentId}`, { method: "PUT", body: payload });
                    showToast(res.message, "success");
                    bootstrap.Modal.getInstance(document.getElementById("modalEditStudent"))?.hide();
                    loadAdminStudents();
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }

        // Issue Book Form Submit
        const formIssueBook = document.getElementById("formIssueBook");
        if (formIssueBook) {
            formIssueBook.addEventListener("submit", async e => {
                e.preventDefault();
                const payload = {
                    book_id: document.getElementById("issueBookSelect").value,
                    student_id: document.getElementById("issueStudentSelect").value,
                    due_date: document.getElementById("issueDueDate").value,
                    notes: document.getElementById("issueNotes").value.trim()
                };

                try {
                    const res = await apiRequest("/api/issue", { method: "POST", body: payload });
                    showToast(res.message, "success");
                    formIssueBook.reset();
                    navigateTo("admin-issued");
                } catch (err) {
                    showToast(err.message, "danger");
                }
            });
        }
    }

    function openEditBookModal(book) {
        document.getElementById("editBookId").value = book.id;
        document.getElementById("editBookTitle").value = book.title;
        document.getElementById("editBookAuthor").value = book.author;
        document.getElementById("editBookCategory").value = book.category;
        document.getElementById("editBookIsbn").value = book.isbn || "";
        document.getElementById("editBookPublisher").value = book.publisher || "";
        document.getElementById("editBookTotalCopies").value = book.total_copies;
        document.getElementById("editBookAvailableCopies").value = book.available_copies;
        document.getElementById("editBookIssuedHint").textContent = `Currently issued: ${book.issued_copies}`;

        const modal = new bootstrap.Modal(document.getElementById("modalEditBook"));
        modal.show();
    }

    function openEditStudentModal(student) {
        document.getElementById("editStudentId").value = student.id;
        document.getElementById("editStudentIdNum").value = student.student_id_number;
        document.getElementById("editStudentName").value = student.full_name;
        document.getElementById("editStudentEmail").value = student.email;
        document.getElementById("editStudentPhone").value = student.phone || "";
        document.getElementById("editStudentDepartment").value = student.department;

        const modal = new bootstrap.Modal(document.getElementById("modalEditStudent"));
        modal.show();
    }

    // App Initialization
    async function init() {
        setupEventListeners();
        await checkAuth();

        const initialHash = window.location.hash.replace("#", "") || "home";
        navigateTo(initialHash);
    }

    document.addEventListener("DOMContentLoaded", init);
})();
