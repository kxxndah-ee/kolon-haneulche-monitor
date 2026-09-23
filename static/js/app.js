// Kolon Global & Haneulche Community Monitoring System Frontend Logic

let currentChannel = "ALL";
let currentRisk = "ALL";
let currentSentiment = "ALL";
let currentSearch = "";
let onlyBookmarked = false;
let currentOffset = 0;
const PAGE_LIMIT = 50;

let trendChartInstance = null;
let channelChartInstance = null;
let sentimentChartInstance = null;

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
    initClock();
    initFilters();
    initModals();
    initActions();
    initSSE();
    loadStats();
    loadPosts(true);
    checkSchedulerStatus();

    // Poll scheduler status every 15s
    setInterval(checkSchedulerStatus, 15000);
});

// 1. KST Clock
function initClock() {
    const clockEl = document.getElementById("kstClock");
    function updateClock() {
        const now = new Date();
        const kstTime = new Intl.DateTimeFormat("ko-KR", {
            timeZone: "Asia/Seoul",
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }).format(now);
        clockEl.textContent = `${kstTime} KST`;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// 2. Filters & Search
function initFilters() {
    // Channel tabs
    const tabs = document.querySelectorAll(".channel-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentChannel = tab.dataset.channel;
            currentOffset = 0;
            loadPosts(true);
        });
    });

    // Risk select
    const riskSelect = document.getElementById("selectRisk");
    riskSelect.addEventListener("change", (e) => {
        currentRisk = e.target.value;
        currentOffset = 0;
        loadPosts(true);
    });

    // Sentiment select
    const sentimentSelect = document.getElementById("selectSentiment");
    sentimentSelect.addEventListener("change", (e) => {
        currentSentiment = e.target.value;
        currentOffset = 0;
        loadPosts(true);
    });

    // Bookmark toggle
    const btnBookmark = document.getElementById("btnOnlyBookmark");
    btnBookmark.addEventListener("click", () => {
        onlyBookmarked = !onlyBookmarked;
        btnBookmark.classList.toggle("active", onlyBookmarked);
        currentOffset = 0;
        loadPosts(true);
    });

    // Search with debounce
    const searchInput = document.getElementById("searchInput");
    const clearBtn = document.getElementById("btnClearSearch");
    let searchTimeout = null;

    searchInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        clearBtn.style.display = val ? "block" : "none";
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearch = val;
            currentOffset = 0;
            loadPosts(true);
        }, 350);
    });

    clearBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearBtn.style.display = "none";
        currentSearch = "";
        currentOffset = 0;
        loadPosts(true);
    });

    // Refresh list button
    document.getElementById("btnRefreshList").addEventListener("click", () => {
        loadStats();
        loadPosts(true);
    });

    // Load more button
    document.getElementById("btnLoadMore").addEventListener("click", () => {
        currentOffset += PAGE_LIMIT;
        loadPosts(false);
    });
}

// 3. Load Posts
async function loadPosts(reset = false) {
    if (reset) {
        currentOffset = 0;
    }

    const params = new URLSearchParams({
        channel: currentChannel,
        risk_level: currentRisk,
        sentiment: currentSentiment,
        only_bookmarked: onlyBookmarked,
        limit: PAGE_LIMIT,
        offset: currentOffset
    });
    if (currentSearch) {
        params.append("search", currentSearch);
    }

    const feedList = document.getElementById("feedList");
    if (reset) {
        feedList.innerHTML = `
            <div class="feed-empty">
                <i data-lucide="loader" class="spinning"></i>
                <p>게시글 목록을 불러오는 중...</p>
            </div>
        `;
        lucide.createIcons();
    }

    try {
        const res = await fetch(`/api/posts?${params.toString()}`);
        const data = await res.json();
        const posts = data.posts || [];

        document.getElementById("feedCountText").textContent = `${posts.length}건 표시 중`;

        if (reset) {
            feedList.innerHTML = "";
        }

        if (posts.length === 0 && reset) {
            feedList.innerHTML = `
                <div class="feed-empty">
                    <i data-lucide="inbox"></i>
                    <p>조건에 맞는 게시글이 없습니다.</p>
                </div>
            `;
            lucide.createIcons();
            document.getElementById("btnLoadMore").style.display = "none";
            return;
        }

        posts.forEach(post => {
            feedList.appendChild(createPostCard(post));
        });

        const btnLoadMore = document.getElementById("btnLoadMore");
        if (posts.length === PAGE_LIMIT) {
            btnLoadMore.style.display = "inline-flex";
        } else {
            btnLoadMore.style.display = "none";
        }

        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load posts:", err);
    }
}

// Create Card Element
function createPostCard(post) {
    const card = document.createElement("div");
    card.className = `post-card ${post.risk_level === "HIGH" ? "risk-high" : post.risk_level === "MEDIUM" ? "risk-medium" : ""} ${post.is_read ? "is-read" : ""}`;
    card.id = `post-${post.id}`;

    // Channel badge class
    let channelClass = "c-news";
    if (post.channel === "네이버 카페") channelClass = "c-naver-cafe";
    else if (post.channel === "네이버 블로그") channelClass = "c-naver-blog";
    else if (post.channel === "다음 카페") channelClass = "c-daum-cafe";
    else if (post.channel === "다음 블로그") channelClass = "c-daum-blog";
    else if (post.channel === "커뮤니티") channelClass = "c-comm";

    // Risk badge class
    let riskClass = "r-safe";
    let riskLabel = "안전";
    if (post.risk_level === "HIGH") { riskClass = "r-high"; riskLabel = "🚨 심각"; }
    else if (post.risk_level === "MEDIUM") { riskClass = "r-medium"; riskLabel = "⚠️ 주의"; }
    else if (post.risk_level === "INFO") { riskClass = "r-info"; riskLabel = "ℹ️ 관심"; }

    // Sentiment badge
    let sentClass = "s-neutral";
    let sentLabel = "중립";
    if (post.sentiment === "NEGATIVE") { sentClass = "s-negative"; sentLabel = "부정"; }
    else if (post.sentiment === "POSITIVE") { sentClass = "s-positive"; sentLabel = "긍정"; }

    const risks = post.detected_risks || [];
    const risksHtml = risks.length > 0 
        ? `<div class="detected-risks-row">
            ${risks.map(r => `<span class="risk-tag-chip">${escapeHtml(r)}</span>`).join("")}
           </div>`
        : "";

    card.innerHTML = `
        <div class="post-card-header">
            <div class="post-badges">
                <span class="channel-badge ${channelClass}">${escapeHtml(post.channel)}</span>
                <span class="risk-badge ${riskClass}">${riskLabel}</span>
                <span class="sentiment-badge ${sentClass}">${sentLabel}</span>
                ${post.keyword ? `<span class="keyword-tag">#${escapeHtml(post.keyword)}</span>` : ""}
            </div>
            <div class="post-meta">
                <span>${escapeHtml(post.source || "")}</span> ·
                <span>${escapeHtml(post.published_at || post.collected_at?.slice(0, 10) || "")}</span>
            </div>
        </div>

        <div class="post-card-body">
            <a href="${escapeHtml(post.url)}" target="_blank" class="post-title-link" onclick="handleCardClick(${post.id})">
                ${escapeHtml(post.title)}
            </a>
            ${post.snippet ? `<p class="post-snippet">${escapeHtml(post.snippet)}</p>` : ""}
            ${risksHtml}
        </div>

        <div class="post-card-footer">
            <span class="post-collected-time">수집: ${escapeHtml(post.collected_at || "")}</span>
            <div class="post-footer-actions">
                <button class="action-btn ${post.is_bookmarked ? 'bookmarked' : ''}" onclick="toggleBookmarkAction(${post.id}, this)">
                    <i data-lucide="${post.is_bookmarked ? 'bookmark-check' : 'bookmark'}"></i>
                    <span>북마크</span>
                </button>
                <button class="action-btn" onclick="openDetailModal(${JSON.stringify(post).replace(/"/g, '&quot;')})">
                    <i data-lucide="maximize-2"></i>
                    <span>상세보기</span>
                </button>
            </div>
        </div>
    `;

    return card;
}

// 4. Statistics and Charts
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const stats = await res.json();

        document.getElementById("valTotalPosts").textContent = Number(stats.total_posts || 0).toLocaleString();
        document.getElementById("valTodayPosts").textContent = Number(stats.today_posts || 0).toLocaleString();
        document.getElementById("valMediumRisk").textContent = Number(stats.medium_risk_count || 0).toLocaleString();
        document.getElementById("valHighRisk").textContent = Number(stats.high_risk_count || 0).toLocaleString();

        renderCharts(stats);
    } catch (err) {
        console.error("Failed to load stats:", err);
    }
}

function renderCharts(stats) {
    // 1. Trend Chart
    const trendCtx = document.getElementById("trendChart")?.getContext("2d");
    if (trendCtx) {
        const trendLabels = (stats.trend || []).map(t => t.date?.slice(5));
        const trendData = (stats.trend || []).map(t => t.count);

        if (trendChartInstance) trendChartInstance.destroy();
        trendChartInstance = new Chart(trendCtx, {
            type: "line",
            data: {
                labels: trendLabels.length ? trendLabels : ["오늘"],
                datasets: [{
                    label: "일자별 수집량",
                    data: trendData.length ? trendData : [stats.today_posts || 0],
                    borderColor: "#0284c7",
                    backgroundColor: "rgba(2, 132, 199, 0.1)",
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
            }
        });
    }

    // 2. Channel Share Doughnut Chart
    const channelCtx = document.getElementById("channelChart")?.getContext("2d");
    if (channelCtx) {
        const dist = stats.channels_dist || {};
        const labels = Object.keys(dist);
        const values = Object.values(dist);

        if (channelChartInstance) channelChartInstance.destroy();
        channelChartInstance = new Chart(channelCtx, {
            type: "doughnut",
            data: {
                labels: labels.length ? labels : ["데이터 없음"],
                datasets: [{
                    data: values.length ? values : [1],
                    backgroundColor: ["#03c75a", "#2db400", "#ff3e3e", "#ff6a00", "#6366f1", "#0284c7"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } }
            }
        });
    }

    // 3. Sentiment & Risk Chart
    const sentCtx = document.getElementById("sentimentChart")?.getContext("2d");
    if (sentCtx) {
        if (sentimentChartInstance) sentimentChartInstance.destroy();
        sentimentChartInstance = new Chart(sentCtx, {
            type: "bar",
            data: {
                labels: ["긍정", "중립", "부정/주의", "고위험"],
                datasets: [{
                    data: [
                        stats.positive_count || 0,
                        stats.neutral_count || 0,
                        stats.medium_risk_count || 0,
                        stats.high_risk_count || 0
                    ],
                    backgroundColor: ["#10b981", "#94a3b8", "#f59e0b", "#f43f5e"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
            }
        });
    }
}

// 5. Actions (Bookmark, Read, Trigger Crawl, Scheduler)
async function toggleBookmarkAction(postId, btnEl) {
    try {
        const res = await fetch(`/api/posts/${postId}/bookmark`, { method: "POST" });
        const data = await res.json();
        btnEl.classList.toggle("bookmarked", data.is_bookmarked);
        const icon = btnEl.querySelector("i");
        if (icon) {
            icon.setAttribute("data-lucide", data.is_bookmarked ? "bookmark-check" : "bookmark");
            lucide.createIcons();
        }
    } catch (err) {
        console.error("Bookmark toggle failed:", err);
    }
}

async function handleCardClick(postId) {
    try {
        await fetch(`/api/posts/${postId}/read`, { method: "POST" });
        const card = document.getElementById(`post-${postId}`);
        if (card) {
            card.classList.add("is-read");
        }
    } catch (err) {}
}

function initActions() {
    // Analytics toggle
    const btnToggleAnalytics = document.getElementById("btnToggleAnalytics");
    const analyticsContainer = document.getElementById("analyticsContainer");
    const analyticsChevron = document.getElementById("analyticsChevron");
    btnToggleAnalytics.addEventListener("click", () => {
        const isClosed = analyticsContainer.style.display === "none";
        analyticsContainer.style.display = isClosed ? "grid" : "none";
        analyticsChevron.style.transform = isClosed ? "rotate(0deg)" : "rotate(180deg)";
    });

    // Trigger Crawl
    const btnTrigger = document.getElementById("btnTriggerCrawl");
    const iconCrawl = document.getElementById("iconCrawl");
    btnTrigger.addEventListener("click", async () => {
        btnTrigger.disabled = true;
        iconCrawl.classList.add("spinning");

        try {
            const res = await fetch("/api/scheduler/trigger", { method: "POST" });
            const data = await res.json();
            alert(data.message || "수집을 시작했습니다.");
            
            // Poll for completion
            let pollCount = 0;
            const pollTimer = setInterval(async () => {
                pollCount++;
                const statusRes = await fetch("/api/scheduler/status");
                const s = await statusRes.json();
                if (!s.is_collecting || pollCount > 30) {
                    clearInterval(pollTimer);
                    btnTrigger.disabled = false;
                    iconCrawl.classList.remove("spinning");
                    loadStats();
                    loadPosts(true);
                }
            }, 3000);
        } catch (err) {
            btnTrigger.disabled = false;
            iconCrawl.classList.remove("spinning");
            alert("수집 요청 중 오류가 발생했습니다.");
        }
    });

    // Toggle Scheduler
    const btnToggle = document.getElementById("btnToggleScheduler");
    const textToggle = document.getElementById("textToggleScheduler");
    btnToggle.addEventListener("click", async () => {
        const res = await fetch("/api/scheduler/toggle", { method: "POST" });
        const data = await res.json();
        updateSchedulerStatusUI(data.is_running);
    });

    // Export Excel
    document.getElementById("btnExportExcel").addEventListener("click", () => {
        const params = new URLSearchParams({
            channel: currentChannel,
            risk_level: currentRisk,
            sentiment: currentSentiment
        });
        if (currentSearch) {
            params.append("search", currentSearch);
        }
        window.location.href = `/api/export/excel?${params.toString()}`;
    });
}

async function checkSchedulerStatus() {
    try {
        const res = await fetch("/api/scheduler/status");
        const data = await res.json();
        updateSchedulerStatusUI(data.is_running, data.is_collecting, data.current_interval);
    } catch (err) {}
}

function updateSchedulerStatusUI(isRunning, isCollecting = false, interval = 15) {
    const dot = document.getElementById("liveDot");
    const text = document.getElementById("schedulerStatusText");
    const btnText = document.getElementById("textToggleScheduler");

    if (isRunning) {
        dot.classList.remove("stopped");
        text.textContent = isCollecting ? "수집 진행 중..." : `자동 수집 활성 (${interval}분 주기)`;
        btnText.textContent = "스케줄러 중지";
    } else {
        dot.classList.add("stopped");
        text.textContent = "스케줄러 일시중지됨";
        btnText.textContent = "스케줄러 시작";
    }
}

// 6. SSE Real-time Updates
function initSSE() {
    const eventSource = new EventSource("/api/stream");
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "connected") return;

            // Prepend new post to feed
            const feedList = document.getElementById("feedList");
            const emptyEl = feedList.querySelector(".feed-empty");
            if (emptyEl) emptyEl.remove();

            feedList.insertBefore(createPostCard(data), feedList.firstChild);
            lucide.createIcons();

            // Refresh stats badge
            loadStats();
        } catch (e) {}
    };
    eventSource.onerror = () => {
        eventSource.close();
        setTimeout(initSSE, 5000);
    };
}

// 7. Modals Logic
function initModals() {
    // Open Keywords
    document.getElementById("btnOpenKeywords").addEventListener("click", () => {
        openModal("modalKeywords");
        loadKeywordsList();
    });

    // Open Settings
    document.getElementById("btnOpenSettings").addEventListener("click", () => {
        openModal("modalSettings");
        loadSettingsForm();
    });

    // Close buttons
    document.querySelectorAll("[data-close]").forEach(btn => {
        btn.addEventListener("click", () => {
            const modalId = btn.getAttribute("data-close");
            closeModal(modalId);
        });
    });

    // Keyword operations
    document.getElementById("btnAddKeyword").addEventListener("click", async () => {
        const input = document.getElementById("inputNewKeyword");
        const val = input.value.trim();
        if (!val) return;
        await fetch("/api/keywords", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword: val })
        });
        input.value = "";
        loadKeywordsList();
    });

    document.getElementById("btnAddNegative").addEventListener("click", async () => {
        const input = document.getElementById("inputNewNegative");
        const val = input.value.trim();
        if (!val) return;
        await fetch("/api/negative-keywords", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword: val })
        });
        input.value = "";
        loadKeywordsList();
    });

    // Save Settings
    document.getElementById("btnSaveSettings").addEventListener("click", async () => {
        const toastEnabled = document.getElementById("chkToastEnabled").checked;
        const telegramEnabled = document.getElementById("chkTelegramEnabled").checked;
        const tgToken = document.getElementById("inputTgToken").value.trim();
        const tgChatId = document.getElementById("inputTgChatId").value.trim();
        const naverId = document.getElementById("inputNaverId").value.trim();
        const naverSecret = document.getElementById("inputNaverSecret").value.trim();
        const kakaoKey = document.getElementById("inputKakaoKey").value.trim();

        const intervalRadio = document.querySelector('input[name="crawlInterval"]:checked');
        const interval = intervalRadio ? parseInt(intervalRadio.value) : 15;

        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                toast_enabled: toastEnabled,
                telegram_enabled: telegramEnabled,
                telegram_bot_token: tgToken,
                telegram_chat_id: tgChatId,
                naver_client_id: naverId,
                naver_client_secret: naverSecret,
                kakao_rest_api_key: kakaoKey
            })
        });

        await fetch("/api/scheduler/interval", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ minutes: interval })
        });

        closeModal("modalSettings");
        alert("설정이 저장되었습니다.");
        checkSchedulerStatus();
    });
}

function openModal(id) {
    document.getElementById(id).classList.add("open");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("open");
}

async function loadKeywordsList() {
    const resK = await fetch("/api/keywords");
    const dataK = await resK.json();
    const containerK = document.getElementById("targetKeywordsList");
    containerK.innerHTML = (dataK.keywords || []).map(kw => `
        <span class="tag-item">
            ${escapeHtml(kw)}
            <button class="tag-remove" onclick="deleteKeywordAction('${escapeHtml(kw)}')">&times;</button>
        </span>
    `).join("");

    const resN = await fetch("/api/negative-keywords");
    const dataN = await resN.json();
    const containerN = document.getElementById("negativeKeywordsList");
    containerN.innerHTML = (dataN.negative_keywords || []).map(nkw => `
        <span class="tag-item">
            ${escapeHtml(nkw)}
            <button class="tag-remove" onclick="deleteNegativeKeywordAction('${escapeHtml(nkw)}')">&times;</button>
        </span>
    `).join("");
}

async function deleteKeywordAction(kw) {
    await fetch(`/api/keywords/${encodeURIComponent(kw)}`, { method: "DELETE" });
    loadKeywordsList();
}

async function deleteNegativeKeywordAction(kw) {
    await fetch(`/api/negative-keywords/${encodeURIComponent(kw)}`, { method: "DELETE" });
    loadKeywordsList();
}

async function loadSettingsForm() {
    const res = await fetch("/api/settings");
    const s = await res.json();
    document.getElementById("chkToastEnabled").checked = s.toast_enabled;
    document.getElementById("chkTelegramEnabled").checked = s.telegram_enabled;
    document.getElementById("inputTgToken").value = s.telegram_bot_token || "";
    document.getElementById("inputTgChatId").value = s.telegram_chat_id || "";
    document.getElementById("inputNaverId").value = s.naver_client_id || "";
    document.getElementById("inputNaverSecret").value = s.naver_client_secret || "";
    document.getElementById("inputKakaoKey").value = s.kakao_rest_api_key || "";

    const radios = document.querySelectorAll('input[name="crawlInterval"]');
    radios.forEach(r => {
        if (parseInt(r.value) === s.default_interval_minutes) {
            r.checked = true;
        }
    });
}

function openDetailModal(post) {
    document.getElementById("detailChannel").textContent = post.channel || "";
    document.getElementById("detailRisk").textContent = post.risk_level === "HIGH" ? "🚨 고위험" : post.risk_level === "MEDIUM" ? "⚠️ 주의" : "정상";
    document.getElementById("detailSentiment").textContent = post.sentiment || "";
    document.getElementById("detailTitle").textContent = post.title || "";
    document.getElementById("detailSource").textContent = post.source || "출처 미상";
    document.getElementById("detailDate").textContent = post.published_at || post.collected_at?.slice(0, 10) || "";
    document.getElementById("detailKeyword").textContent = post.keyword ? `#${post.keyword}` : "";

    const risks = post.detected_risks || [];
    const risksBox = document.getElementById("detailRisksBox");
    const risksTags = document.getElementById("detailRiskTags");
    if (risks.length > 0) {
        risksBox.style.display = "block";
        risksTags.innerHTML = risks.map(r => `<span class="risk-tag-chip">${escapeHtml(r)}</span>`).join("");
    } else {
        risksBox.style.display = "none";
    }

    document.getElementById("detailSnippet").textContent = post.snippet || "본문 내용 요약이 없습니다.";
    document.getElementById("btnDetailOpenUrl").href = post.url;

    openModal("modalPostDetail");
    lucide.createIcons();
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
