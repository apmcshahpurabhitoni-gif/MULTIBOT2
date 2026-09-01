"use strict";

/*
 * MULTIBOT2 dashboard controller.
 *
 * Frontend responsibilities:
 * - navigation
 * - theme/style controls
 * - IST clock
 * - rendering backend data
 * - signal freshness display
 *
 * Frontend must NOT calculate:
 * - strategy signals
 * - entry
 * - stop-loss
 * - take-profit
 * - position sizing
 * - risk
 */


/* =========================================================
   CONFIGURATION
   ========================================================= */

const CONFIG = Object.freeze({
    apiUrl:
        window.DASHBOARD_API_URL ||
        "/api/dashboard",

    timezone:
        "Asia/Kolkata",

    freshnessHours: 1,

    refreshMs: 30_000,
});


const SCHEDULE = Object.freeze([
    "09:15",
    "10:15",
    "11:15",
    "12:15",
    "13:15",
    "14:15",
]);


/* =========================================================
   STATE
   ========================================================= */

let dashboardData = {
    system: {
        status: "WAITING",
        mode: "PAPER",
    },

    rules: {},

    universe: {
        count: 15,
        symbols: [],
        fixed: true,
    },

    accounts: {
        count: 4,
        names: [],
        data: [],
    },

    signals: [],

    trades: [],
};

let lastUpdate = null;


/* =========================================================
   DOM HELPERS
   ========================================================= */

function byId(id) {
    return document.getElementById(id);
}


/* =========================================================
   HTML SAFETY
   ========================================================= */

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   NUMBER FORMATTING
   ========================================================= */

function formatINR(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return `₹${number.toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }
    )}`;
}


function formatPrice(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return number.toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }
    );
}


/* =========================================================
   TIME FORMATTING
   ========================================================= */

function formatTimestamp(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "—";
    }

    return new Intl.DateTimeFormat(
        "en-IN",
        {
            timeZone: CONFIG.timezone,
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        }
    ).format(date);
}


function formatClock(
    date = new Date()
) {
    return new Intl.DateTimeFormat(
        "en-IN",
        {
            timeZone: CONFIG.timezone,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
        }
    ).format(date);
}


/* =========================================================
   FRESHNESS
   ========================================================= */

function getFreshness(timestamp) {
    if (!timestamp) {
        return {
            label: "UNKNOWN",
            className: "stale",
        };
    }

    const signalDate = new Date(timestamp);

    if (
        Number.isNaN(
            signalDate.getTime()
        )
    ) {
        return {
            label: "INVALID",
            className: "stale",
        };
    }

    const ageMs =
        Date.now()
        - signalDate.getTime();

    if (ageMs < 0) {
        return {
            label: "INVALID",
            className: "stale",
        };
    }

    const ageHours =
        ageMs /
        (60 * 60 * 1000);

    if (
        ageHours <=
        CONFIG.freshnessHours
    ) {
        return {
            label: "FRESH",
            className: "fresh",
        };
    }

    return {
        label: "STALE",
        className: "stale",
    };
}


/* =========================================================
   SIGNAL HELPERS
   ========================================================= */

function signalClass(signal) {
    const normalized =
        String(
            signal || "NO_SIGNAL"
        )
            .toLowerCase()
            .replaceAll("_", "-");

    if (
        normalized === "buy" ||
        normalized === "sell" ||
        normalized === "neutral" ||
        normalized === "no-signal"
    ) {
        return normalized;
    }

    return "no-signal";
}


function signalDirection(signal) {
    const normalized =
        String(
            signal || "NO_SIGNAL"
        ).toUpperCase();

    if (
        normalized === "NO_SIGNAL"
    ) {
        return "NO SIGNAL";
    }

    return normalized;
}


/* =========================================================
   SIGNAL RENDERING
   ========================================================= */

function renderSignal(signal) {
    const freshness =
        getFreshness(
            signal.timestamp
        );

    const directionClass =
        signalClass(
            signal.signal
        );

    return `
        <div class="signal-card">

            <div class="signal-top">

                <div class="signal-identity">

                    <div class="signal-strategy">
                        ${escapeHtml(
                            signal.strategy ||
                            "Strategy"
                        )}
                    </div>

                    <div class="signal-symbol">
                        ${escapeHtml(
                            signal.symbol ||
                            signal.asset ||
                            ""
                        )}
                    </div>

                </div>


                <div
                    class="signal-direction ${directionClass}"
                >
                    ${escapeHtml(
                        signalDirection(
                            signal.signal
                        )
                    )}
                </div>

            </div>


            <div class="signal-details">

                <div class="signal-detail">

                    <span>
                        Timestamp
                    </span>

                    <strong>
                        ${escapeHtml(
                            formatTimestamp(
                                signal.timestamp
                            )
                        )}
                    </strong>

                </div>


                <div class="signal-detail">

                    <span>
                        Timeframe
                    </span>

                    <strong>
                        ${escapeHtml(
                            signal.timeframe ||
                            "1H"
                        )}
                    </strong>

                </div>


                <div class="signal-detail">

                    <span>
                        Reason
                    </span>

                    <strong>
                        ${escapeHtml(
                            signal.reason ||
                            "—"
                        )}
                    </strong>

                </div>

            </div>


            <div
                class="freshness ${freshness.className}"
            >
                ${freshness.label}
            </div>

        </div>
    `;
}


/* =========================================================
   TRADE RENDERING
   ========================================================= */

function renderTrade(trade) {
    const plan =
        trade.plan || {};

    const side =
        String(
            plan.side || ""
        ).toUpperCase();

    const sideClass =
        side === "BUY"
            ? "positive"
            : side === "SELL"
                ? "negative"
                : "";

    return `
        <div class="trade-card">

            <div class="trade-header">

                <div class="trade-title">

                    ${escapeHtml(
                        plan.strategy ||
                        "Strategy"
                    )}

                    ·

                    <span class="${sideClass}">
                        ${escapeHtml(
                            side || "—"
                        )}
                    </span>

                </div>


                <div
                    class="trade-status ${
                        String(
                            trade.status ||
                            "OPEN"
                        ).toLowerCase()
                    }"
                >
                    ${escapeHtml(
                        trade.status ||
                        "OPEN"
                    )}
                </div>

            </div>


            <div class="trade-grid">

                <div class="trade-field">

                    <span>
                        Entry
                    </span>

                    <strong>
                        ${formatPrice(
                            plan.entry
                        )}
                    </strong>

                </div>


                <div class="trade-field">

                    <span>
                        Stop Loss
                    </span>

                    <strong class="negative">
                        ${formatPrice(
                            plan.stop_loss
                        )}
                    </strong>

                </div>


                <div class="trade-field">

                    <span>
                        Take Profit
                    </span>

                    <strong class="positive">
                        ${formatPrice(
                            plan.take_profit
                        )}
                    </strong>

                </div>


                <div class="trade-field">

                    <span>
                        Signal
                    </span>

                    <strong>
                        ${escapeHtml(
                            formatTimestamp(
                                plan.signal_timestamp
                            )
                        )}
                    </strong>

                </div>

            </div>

        </div>
    `;
}


/* =========================================================
   OVERVIEW
   ========================================================= */

function renderOverview() {
    const signals =
        Array.isArray(
            dashboardData.signals
        )
            ? dashboardData.signals
            : [];

    const trades =
        Array.isArray(
            dashboardData.trades
        )
            ? dashboardData.trades
            : [];

    const openTrades =
        trades.filter(
            trade =>
                String(
                    trade.status || ""
                ).toUpperCase()
                === "OPEN"
        );


    const status =
        dashboardData.system?.status ||
        "WAITING";


    byId(
        "overviewSystem"
    ).textContent =
        status;


    byId(
        "overviewSignalCount"
    ).textContent =
        signals.length;


    byId(
        "overviewTradeCount"
    ).textContent =
        openTrades.length;


    byId(
        "overviewUpdated"
    ).textContent =
        lastUpdate
            ? formatTimestamp(
                lastUpdate
            )
            : "—";


    const overviewSignals =
        byId(
            "overviewSignals"
        );


    if (!signals.length) {

        overviewSignals.innerHTML = `
            <div class="empty-state">
                No signals loaded.
            </div>
        `;

    } else {

        overviewSignals.innerHTML =
            signals
                .slice(0, 5)
                .map(renderSignal)
                .join("");
    }


    const overviewTrades =
        byId(
            "overviewTrades"
        );


    if (!openTrades.length) {

        overviewTrades.innerHTML = `
            <div class="empty-state">
                No open trades.
            </div>
        `;

    } else {

        overviewTrades.innerHTML =
            openTrades
                .slice(0, 5)
                .map(renderTrade)
                .join("");
    }
}


/* =========================================================
   TRADES
   ========================================================= */

function renderTrades() {
    const container =
        byId("tradesList");

    const trades =
        Array.isArray(
            dashboardData.trades
        )
            ? dashboardData.trades
            : [];


    const openTrades =
        trades.filter(
            trade =>
                String(
                    trade.status || ""
                ).toUpperCase()
                === "OPEN"
        );


    const closedTrades =
        trades.filter(
            trade =>
                String(
                    trade.status || ""
                ).toUpperCase()
                === "CLOSED"
        );


    byId(
        "tradesOpenCount"
    ).textContent =
        openTrades.length;


    byId(
        "tradesClosedCount"
    ).textContent =
        closedTrades.length;


    if (!openTrades.length) {

        container.innerHTML = `
            <div class="empty-state">
                No open trades.
            </div>
        `;

        return;
    }


    container.innerHTML =
        openTrades
            .map(renderTrade)
            .join("");
}


/* =========================================================
   SIGNALS PAGE
   ========================================================= */

function renderSignals() {
    const container =
        byId("signalsList");

    const signals =
        Array.isArray(
            dashboardData.signals
        )
            ? dashboardData.signals
            : [];


    if (!signals.length) {

        container.innerHTML = `
            <div class="empty-state">
                No signals loaded.
            </div>
        `;

        return;
    }


    container.innerHTML =
        signals
            .map(renderSignal)
            .join("");
}


/* =========================================================
   HISTORY
   ========================================================= */

function renderHistory() {
    const container =
        byId("historyList");

    const trades =
        Array.isArray(
            dashboardData.trades
        )
            ? dashboardData.trades
            : [];


    const closedTrades =
        trades.filter(
            trade =>
                String(
                    trade.status || ""
                ).toUpperCase()
                === "CLOSED"
        );


    if (!closedTrades.length) {

        container.innerHTML = `
            <div class="empty-state">
                No historical records loaded.
            </div>
        `;

        return;
    }


    container.innerHTML =
        closedTrades
            .map(renderTrade)
            .join("");
}


/* =========================================================
   NEWS
   ========================================================= */

function renderNews() {
    const container =
        byId("newsList");

    const news =
        Array.isArray(
            dashboardData.news
        )
            ? dashboardData.news
            : [];


    if (!news.length) {

        container.innerHTML = `
            <div class="empty-state">
                No news loaded.
            </div>
        `;

        return;
    }


    container.innerHTML =
        news
            .map(item => `
                <div class="signal-card">

                    <div class="signal-strategy">
                        ${escapeHtml(
                            item.title ||
                            "Market update"
                        )}
                    </div>

                    <div class="signal-symbol">
                        ${escapeHtml(
                            item.source ||
                            ""
                        )}
                    </div>

                </div>
            `)
            .join("");
}


/* =========================================================
   SCHEDULE
   ========================================================= */

function renderSchedule() {
    const container =
        byId(
            "candleSchedule"
        );

    container.innerHTML =
        SCHEDULE
            .map(time => `
                <div class="schedule-item">
                    ${time}
                </div>
            `)
            .join("");
}


/* =========================================================
   SYSTEM STATUS
   ========================================================= */

function renderSystemStatus() {
    const status =
        String(
            dashboardData.system?.status ||
            "WAITING"
        ).toUpperCase();


    byId(
        "systemStatus"
    ).textContent =
        status;


    byId(
        "overviewSystem"
    ).textContent =
        status;


    const dot =
        byId(
            "systemStatusDot"
        );


    dot.style.opacity =
        status === "ONLINE"
            ? "1"
            : "0.45";
}


/* =========================================================
   DASHBOARD RENDER
   ========================================================= */

function renderDashboard() {
    renderSystemStatus();

    renderOverview();

    renderSignals();

    renderTrades();

    renderHistory();

    renderNews();

    renderSchedule();
}


/* =========================================================
   PAYLOAD VALIDATION
   ========================================================= */

function normalizeDashboardPayload(
    payload
) {
    if (
        !payload ||
        typeof payload !== "object"
    ) {
        throw new Error(
            "Dashboard API returned invalid data"
        );
    }


    return {
        system:
            payload.system &&
            typeof payload.system ===
                "object"
                ? payload.system
                : {
                    status: "WAITING",
                    mode: "PAPER",
                },


        rules:
            payload.rules &&
            typeof payload.rules ===
                "object"
                ? payload.rules
                : {},


        universe:
            payload.universe &&
            typeof payload.universe ===
                "object"
                ? payload.universe
                : {
                    count: 15,
                    symbols: [],
                    fixed: true,
                },


        accounts:
            payload.accounts &&
            typeof payload.accounts ===
                "object"
                ? payload.accounts
                : {
                    count: 4,
                    names: [],
                    data: [],
                },


        signals:
            Array.isArray(
                payload.signals
            )
                ? payload.signals
                : [],


        trades:
            Array.isArray(
                payload.trades
            )
                ? payload.trades
                : [],


        news:
            Array.isArray(
                payload.news
            )
                ? payload.news
                : [],
    };
}


/* =========================================================
   API
   ========================================================= */

async function loadDashboard() {
    try {

        const response =
            await fetch(
                CONFIG.apiUrl,
                {
                    method: "GET",
                    cache: "no-store",

                    headers: {
                        Accept:
                            "application/json",
                    },
                }
            );


        if (!response.ok) {

            throw new Error(
                `Dashboard API returned ${response.status}`
            );
        }


        const payload =
            await response.json();


        dashboardData =
            normalizeDashboardPayload(
                payload
            );


        lastUpdate =
            new Date();


        renderDashboard();

    } catch (error) {

        console.error(
            "Dashboard update failed:",
            error
        );

        dashboardData.system = {
            status: "WAITING",
            mode: "PAPER",
        };

        renderSystemStatus();
    }
}


/* =========================================================
   NAVIGATION
   ========================================================= */

function showPage(
    pageName
) {
    document
        .querySelectorAll(
            ".page"
        )
        .forEach(page => {

            page.classList.toggle(
                "active",
                page.id ===
                    `page-${pageName}`
            );

        });


    document
        .querySelectorAll(
            ".nav-button, .mobile-nav-button"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.page ===
                    pageName
            );

        });


    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}


function setupNavigation() {

    document
        .querySelectorAll(
            ".nav-button, .mobile-nav-button"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    showPage(
                        button.dataset.page
                    );

                }
            );

        });


    document
        .querySelectorAll(
            "[data-page-link]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    showPage(
                        button.dataset.pageLink
                    );

                }
            );

        });
}


/* =========================================================
   THEME / STYLE
   ========================================================= */

function setupThemes() {
    const root =
        document.documentElement;


    document
        .querySelectorAll(
            "[data-theme]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const theme =
                        button.dataset.theme;

                    root.dataset.theme =
                        theme;


                    document
                        .querySelectorAll(
                            "[data-theme]"
                        )
                        .forEach(item => {

                            item.classList.toggle(
                                "active",
                                item.dataset.theme ===
                                    theme
                            );

                        });


                    localStorage.setItem(
                        "multibot2-theme",
                        theme
                    );

                }
            );

        });


    document
        .querySelectorAll(
            "[data-style]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const style =
                        button.dataset.style;

                    root.dataset.style =
                        style;


                    document
                        .querySelectorAll(
                            "[data-style]"
                        )
                        .forEach(item => {

                            item.classList.toggle(
                                "active",
                                item.dataset.style ===
                                    style
                            );

                        });


                    localStorage.setItem(
                        "multibot2-style",
                        style
                    );

                }
            );

        });


    const savedTheme =
        localStorage.getItem(
            "multibot2-theme"
        );


    const savedStyle =
        localStorage.getItem(
            "multibot2-style"
        );


    if (
        savedTheme === "light" ||
        savedTheme === "dark"
    ) {

        root.dataset.theme =
            savedTheme;
    }


    if (
        savedStyle === "modern" ||
        savedStyle === "neo"
    ) {

        root.dataset.style =
            savedStyle;
    }


    byId(
        "themeToggle"
    ).addEventListener(
        "click",
        () => {

            const next =
                root.dataset.theme ===
                    "dark"
                    ? "light"
                    : "dark";


            root.dataset.theme =
                next;


            localStorage.setItem(
                "multibot2-theme",
                next
            );

        }
    );
}


/* =========================================================
   CLOCK
   ========================================================= */

function updateClock() {
    byId(
        "marketClock"
    ).textContent =
        formatClock();
}


/* =========================================================
   START
   ========================================================= */

function startDashboard() {

    setupNavigation();

    setupThemes();

    renderSchedule();

    updateClock();

    setInterval(
        updateClock,
        1000
    );

    loadDashboard();

    setInterval(
        loadDashboard,
        CONFIG.refreshMs
    );
}


document.addEventListener(
    "DOMContentLoaded",
    startDashboard
);
