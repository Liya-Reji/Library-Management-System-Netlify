// Library Management System - Frontend Configuration
// When on Netlify, relative "/api" calls route directly to the Netlify Serverless Function via _redirects.
// When on localhost (port 5000), it routes directly to local Flask.

(function () {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

    let apiBase = "";
    if (isLocalhost && window.location.port !== "5000" && window.location.port !== "") {
        apiBase = "http://localhost:5000";
    } else {
        apiBase = "";
    }

    window.API_BASE_URL = apiBase;
})();
