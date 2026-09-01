/*
 * MULTIBOT2 dashboard controller.
 *
 * This file is presentation logic only.
 * It does not calculate strategy signals, entries, SL, TP or risk.
 */

"use strict";

const CONFIG = {
    apiUrl: window.DASHBOARD_API_URL || "/api/dashboard",
    freshnessHours: 1,
    timezone: "Asia/Kolkata",
    refreshMs: 30_000,
};

const SCHEDULE = [
    "09:15",
    "10:15",
    "11:15",
    "12:15",
    "13:15",
    "14:15",
];

let dashboardData = {
    system: {
        status: "WAITING",
        mode: "PAPER",
    },
    signals: [],
    trades: [],
};

let lastUpdate = null;


/* =========================================================
   DOM
   ========================================================= */

function byId(id) {
    return document.getElementById(id);
}


/* =========================================================
   SAFETY / FORMATTING
   ========================================================= */

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatPrice(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return number.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}


function formatTimestamp(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "—";
    }

    return new Intl.DateTimeFormat("en-IN", {
        timeZone: CONFIG.timezone,
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    }).format(date);
}


function formatClock(date = new Date()) {
    return new Intl.DateTimeFormat("en-IN", {
        timeZone: CONFIG.timezone,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    }).format(date);
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

    if (Number.isNaN(signalDate.getTime())) {
        return {
            label: "UNKNOWN",
            className: "stale",
        };
    }

    const ageMs = Date.now() - signalDate.getTime();

    if (ageMs < 0) {
        return {
            label: "INVALID",
            className: "stale",
        };
    }

    const ageHours = ageMs / (60 * 60 * 1000);

    if (ageHours <= CONFIG.freshnessHours) {
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
   SIGNAL RENDERING
   ========================================================= */

function signalClass(signal) {
    const value = String(signal || "NO_SIGNAL")
        .toLowerCase();

    if (
        value === "buy" ||
        value === "sell" ||
        value === "neutral" ||
        value === "no-signal" ||
        value === "no_signal"
    ) {
        return value.replace("_", "-");
    }

    return "no-signal";
}


function signalDirection(signal) {
    const value = String(signal || "NO_SIGNAL");

    if (value === "NO_SIGNAL") {
        return "NO SIGNAL";
    }

    return value;
}


function renderSignal(signal) {
    const freshness = getFreshness(
        signal.timestamp
    );

    const directionClass = signalClass(
        signal.signal
    );

    return `
        <div class="signal-card">

            <div class="signal-top">

                <div class="signal-identity">

                    <div class="signal-strategy">
                        ${escapeHtml(
                            signal.strategy || "Strategy"
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
                        signalDirection(signal.signal)
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
                            signal.timeframe || "1H"
                        )}
                    </strong>

                </div>


                <div class="signal-detail">

                    <span>
                        Reason
                    </span>

                    <strong>
                        ${escapeHtml(
                            signal.reason || "—"
                        )}
                    </strong>

                </div>

            </div>


            <div
                class="freshness ${freshness.className}"
            >
                ${freshness.label}
                ·
                ${escapeHtml(
                    formatTimestamp(
                        signal.timestamp
                    )
                )}
            </div>

        </div>
    `;
}


/* =========================================================
   TRADE RENDERING
   ========================================================= */

function renderTrade(trade) {
    const plan = trade.plan || {};

    return `
        <div class="trade-card">

            <div class="trade-header">

                <div class="trade-title">

                    ${escapeHtml(
                        plan.strategy || "Strategy"
                    )}

                    ·

                    ${escapeHtml(
                        plan.side || "—"
                    )}

                </div>

                <div
                    class="trade-status ${
                        String(
                            trade.status || "OPEN"
                        ).toLowerCase()
                    }"
                >
                    ${escapeHtml(
                        trade.status || "OPEN"
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
    const signals = Array.isArray(
        dashboardData.signals
    )
        ? dashboardData.signals
        : [];

    const trades = Array.isArray(
        dashboardData.trades
    )
        ? dashboardData.trades
        : [];

    const openTrades = trades.filter(
        trade =>
            String(
                trade.status || ""
            ).toUpperCase() === "OPEN"
    );

    const systemStatus =
        dashboardData.system?.status ||
        "WAITING";

    byId("overviewSystem").textContent =
        systemStatus;

    byId("overviewSignalCount").textContent =
        signals.length;

    byId("overviewTradeCount").textContent =
        openTrades.length;

    byId("overviewUpdated").textContent =
        lastUpdate
            ? formatTimestamp(lastUpdate)
            : "—";


    const overviewSignals =
        byId("overviewSignals");

    if (!signals.length) {
        overviewSignals.innerHTML =
            `
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
        byId("overviewTrades");

    if (!openTrades.length) {
        overviewTrades.innerHTML =
            `
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
   SIGNALS PAGE
   ========================================================= */

function renderSignals() {
    const container =
        byId("signalsList");

    const signals = Array.isArray(
        dashboardData.signals
    )
        ? dashboardData.signals
        : [];

    if (!signals.length) {
        container.innerHTML =
            `
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
   TRADES PAGE
   ========================================================= */

function renderTrades() {
    const container =
        byId("tradesList");

    const trades = Array.isArray(
        dashboardData.trades
    )
        ? dashboardData.trades
        : [];

    const openTrades = trades.filter(
        trade =>
            String(
                trade.status || ""
            ).toUpperCase() === "OPEN"
    );

    const closedTrades = trades.filter(
        trade =>
            String(
                trade.status || ""
            ).toUpperCase() === "CLOSED"
    );

    byId("tradesOpenCount").textContent =
        openTrades.length;

    byId("tradesClosedCount").textContent =
        closedTrades.length;

    if (!openTrades.length) {
        container.innerHTML =
            `
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
   HISTORY
   ========================================================= */

function renderHistory() {
    const container =
        byId("historyList");

    const trades = Array.isArray(
        dashboardData.trades
    )
        ? dashboardData.trades
        : [];

    const closedTrades = trades.filter(
        trade =>
            String(
                trade.status || ""
            ).toUpperCase() === "CLOSED"
    );

    if (!closedTrades.length) {
        container.innerHTML =
            `
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

    const news = Array.isArray(
        dashboardData.news
    )
        ? dashboardData.news
        : [];

    if (!news.length) {
        container.innerHTML =
            `
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
                            item.source || ""
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
        byId("candleSchedule");

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

    byId("systemStatus").textContent =
        status;

    byId("overviewSystem").textContent =
        status;

    byId("systemStatusDot").className =
        "status-dot";

    if (status !== "ONLINE") {
        byId("systemStatusDot").style.opacity =
            "0.45";
    } else {
        byId("systemStatusDot").style.opacity =
            "1";
    }
}


/* =========================================================
   COMPLETE RENDER
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
   DATA VALIDATION
   ========================================================= */

function normalizeDashboardPayload(payload) {
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
            typeof payload.system === "object"
                ? payload.system
                : {
                    status: "WAITING",
                    mode: "PAPER",
                },

        signals:
            Array.isArray(payload.signals)
                ? payload.signals
                : [],

        trades:
            Array.isArray(payload.trades)
                ? payload.trades
                : [],

        news:
            Array.isArray(payload.news)
                ? payload.news
                : [],
    };
}


/* =========================================================
   LOAD DATA
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

function showPage(pageName) {
    document
        .querySelectorAll(".page")
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
   THEME
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

                    root.dataset.theme =
                        button.dataset.theme;

                    document
                        .querySelectorAll(
                            "[data-theme]"
                        )
                        .forEach(item => {

                            item.classList.toggle(
                                "active",
                                item.dataset.theme ===
                                    button.dataset.theme
                            );

                        });

                    localStorage.setItem(
                        "multibot2-theme",
                        button.dataset.theme
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

                    root.dataset.style =
                        button.dataset.style;

                    document
                        .querySelectorAll(
                            "[data-style]"
                        )
                        .forEach(item => {

                            item.classList.toggle(
                                "active",
                                item.dataset.style ===
                                    button.dataset.style
                            );

                        });

                    localStorage.setItem(
                        "multibot2-style",
                        button.dataset.style
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


    byId("themeToggle")
        .addEventListener(
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
    byId("marketClock").textContent =
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
