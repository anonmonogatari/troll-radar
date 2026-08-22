// TrollRadar Main Frontend Application

let currentDays = 7;
let currentTab = 'briefing';
let timelineChartInstance = null;
let categoryChartInstance = null;
let entryOffset = 0;
const entryLimit = 20;
let totalEntriesCount = 0;
let authorsDataCache = [];
let networkDataCache = null;
let activeScrapeJobId = null;
let scrapePollTimer = null;

// Smart API fetcher: works on both live FastAPI backend and static GitHub Pages
async function fetchApi(endpoint, fallbackStaticPath) {
    try {
        const res = await fetch(endpoint);
        if (res.ok) {
            return await res.json();
        }
        throw new Error(`HTTP ${res.status}`);
    } catch (e) {
        if (fallbackStaticPath) {
            const staticRes = await fetch(fallbackStaticPath);
            if (staticRes.ok) {
                return await staticRes.json();
            }
        }
        throw e;
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initApp();
});

async function initApp() {
    await loadOverviewStats();
    await loadNarrativeBriefing();
    await loadAuthors();
    loadAnalytics();
    loadNetwork();
    loadEntries();
}

// ----------------- TAB NAVIGATION ----------------- //

function switchTab(tabId) {
    currentTab = tabId;
    
    // Update button styles
    document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`tab-btn-${tabId}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Show / Hide Views
    ['briefing', 'analytics', 'network', 'authors', 'entries'].forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) {
            if (v === tabId) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });

    if (tabId === 'analytics') {
        loadAnalytics();
    } else if (tabId === 'network') {
        loadNetwork();
    } else if (tabId === 'entries') {
        loadEntries();
    } else if (tabId === 'authors') {
        loadAuthors();
    }

    lucide.createIcons();
}

function changeDays(days) {
    currentDays = days;
    document.querySelectorAll('.range-btn').forEach(btn => {
        if (parseInt(btn.getAttribute('data-days')) === days) {
            btn.classList.add('active', 'bg-blue-600', 'text-white', 'font-semibold', 'shadow');
            btn.classList.remove('text-slate-300');
        } else {
            btn.classList.remove('active', 'bg-blue-600', 'text-white', 'font-semibold', 'shadow');
        }
    });

    // Reload active components
    loadOverviewStats();
    loadNarrativeBriefing();
    loadAuthors();
    if (currentTab === 'analytics') loadAnalytics();
    if (currentTab === 'network') loadNetwork();
    if (currentTab === 'entries') loadEntries();
}

// ----------------- OVERVIEW STATS & KPIS ----------------- //

async function loadOverviewStats() {
    try {
        const data = await fetchApi(`/api/stats?days=${currentDays}`, `./data/stats_${currentDays}.json`);

        document.getElementById('kpi-authors').innerText = data.total_monitored_authors || 27;
        document.getElementById('kpi-active-authors').innerText = data.active_authors || 0;
        document.getElementById('kpi-entries').innerText = data.total_entries || 0;
        document.getElementById('kpi-topics-count').innerText = data.total_topics || 0;
        document.getElementById('kpi-coordinated').innerText = data.total_operations || data.coordinated_entries || 0;

        // Top Category
        const cats = data.categories || {};
        const sortedCats = Object.entries(cats).sort((a, b) => b[1] - a[1]);
        if (sortedCats.length > 0) {
            document.getElementById('kpi-top-category').innerText = sortedCats[0][0];
        } else {
            document.getElementById('kpi-top-category').innerText = "Kültür Savaşı & Yaşam Tarzı";
        }

        return data;
    } catch (err) {
        console.error("Failed to load overview stats:", err);
    }
}

// ----------------- TAB 1: NARRATIVE BRIEFING ----------------- //

async function loadNarrativeBriefing() {
    const container = document.getElementById('narratives-container');
    container.innerHTML = `
        <div class="glass-panel p-8 text-center text-slate-400">
            <div class="inline-block animate-spin mb-3 text-blue-400"><i data-lucide="loader-2" class="w-8 h-8"></i></div>
            <p>Haftalık manipülasyon anlatıları ve delil entryler derleniyor...</p>
        </div>
    `;
    lucide.createIcons();

    try {
        const data = await fetchApi(`/api/narratives?days=${currentDays}`, `./data/narratives_${currentDays}.json`);
        const narratives = data.narratives || [];

        if (narratives.length === 0) {
            container.innerHTML = `
                <div class="glass-panel p-8 text-center text-slate-400">
                    <i data-lucide="info" class="w-8 h-8 mx-auto mb-2 text-slate-500"></i>
                    <p>Seçili zaman aralığında tespit edilen manipülasyon anlatısı bulunamadı.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        let html = '';
        narratives.forEach((n, idx) => {
            const eksiSearchUrl = `https://eksisozluk.com/?q=${encodeURIComponent(n.topic)}`;
            const categoryColors = {
                'Kültür Savaşı & Yaşam Tarzı': 'bg-red-500/20 text-red-400 border-red-500/30',
                'Ekonomi Savunması & Aklama': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
                'Muhalefet & Belediye Karalama': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
                'Yargı, Güvenlik & Hamaset': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
                'Suni Gündem & Viral Çarpıtma': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
                'Dış Politika & Jeopolitik Savunma': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
            };
            const catBadgeClass = categoryColors[n.category] || 'bg-slate-700 text-slate-300 border-slate-600';

            html += `
                <div class="glass-panel p-6 border-l-4 ${n.is_coordinated ? 'border-red-500' : 'border-blue-500'} space-y-4">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
                        <div class="flex flex-wrap items-center gap-2">
                            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${catBadgeClass}">
                                ${n.category}
                            </span>
                            ${n.is_coordinated ? `
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1">
                                    <span class="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping"></span> KOORDİNELİ SALDIRI
                                </span>
                            ` : ''}
                            <span class="text-xs text-slate-400 font-mono">
                                👥 ${n.author_count} Yazar / 📝 ${n.entry_count} Entry
                            </span>
                        </div>
                        <a href="${eksiSearchUrl}" target="_blank" class="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 font-semibold">
                            <span>Sözlükte Gör</span>
                            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        </a>
                    </div>

                    <div>
                        <h3 class="text-lg font-bold text-white tracking-tight">
                            # ${escapeHtml(n.topic)}
                        </h3>
                        <p class="text-xs text-slate-300 mt-1 font-medium">
                            ${escapeHtml(n.summary)}
                        </p>
                    </div>

                    <!-- Authors involved badges -->
                    <div class="flex flex-wrap items-center gap-1.5 pt-1">
                        <span class="text-[11px] text-slate-400 mr-1 font-semibold">Aktif Hesaplar:</span>
                        ${n.authors.map(a => `
                            <button onclick="openAuthorModal('${escapeHtml(a)}')" class="px-2 py-0.5 bg-dark-900 hover:bg-dark-700 border border-white/10 rounded text-[11px] text-blue-400 font-mono transition-all">
                                @${escapeHtml(a)}
                            </button>
                        `).join('')}
                    </div>

                    <!-- Chronological Sample Entry Quotes -->
                    <div class="space-y-2 mt-3 pt-3 border-t border-white/5">
                        <h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tespit Edilen Koordineli Entry Alıntıları:</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            ${n.sample_entries.map(s => `
                                <div class="bg-dark-900/80 border border-white/5 rounded-xl p-3.5 space-y-2 hover:border-white/15 transition-all">
                                    <div class="flex items-center justify-between text-[11px]">
                                        <button onclick="openAuthorModal('${escapeHtml(s.author)}')" class="font-bold text-blue-400 hover:underline">
                                            @${escapeHtml(s.author)}
                                        </button>
                                        <span class="text-slate-400 font-mono">${s.date_str || s.created_at.replace('T', ' ').substring(0, 16)}</span>
                                    </div>
                                    <p class="text-xs text-slate-300 italic leading-relaxed">
                                        "${escapeHtml(s.content)}"
                                    </p>
                                    <div class="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                                        <a href="https://eksisozluk.com/entry/${s.id}" target="_blank" class="hover:text-blue-300">#${s.id}</a>
                                        ${s.is_coordinated ? '<span class="text-red-400 font-semibold">⚡ Eşzamanlı</span>' : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                </div>
            `;
        });

        container.innerHTML = html;
        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load narratives:", err);
    }
}

// ----------------- TAB 2: ANALYTICS & CHARTS ----------------- //

async function loadAnalytics() {
    try {
        const stats = await loadOverviewStats();
        
        // 1. Timeline Chart
        if (stats && stats.timeline) {
            renderTimelineChart(stats.timeline);
        }

        // 2. Category Donut Chart
        if (stats && stats.categories) {
            renderCategoryChart(stats.categories);
        }

        // 3. Heatmap
        const heatData = await fetchApi(`/api/heatmap?days=${currentDays}`, `./data/heatmap_${currentDays}.json`);
        renderHeatmap(heatData.heatmap || []);

        // 4. Keywords
        const keyData = await fetchApi(`/api/keywords?days=${currentDays}&limit=30`, `./data/keywords_${currentDays}.json`);
        renderKeywords(keyData.keywords || []);

    } catch (err) {
        console.error("Failed to load analytics:", err);
    }
}

function renderTimelineChart(timeline) {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    const labels = timeline.map(t => t.day);
    const totalData = timeline.map(t => t.total);
    const coordData = timeline.map(t => t.coordinated);

    if (timelineChartInstance) {
        timelineChartInstance.destroy();
    }

    timelineChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Toplam Entry',
                    data: totalData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointBackgroundColor: '#3b82f6'
                },
                {
                    label: 'Koordineli / Eşzamanlı',
                    data: coordData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointBackgroundColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { size: 11, family: 'Plus Jakarta Sans' } }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#64748b', font: { size: 10 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                y: {
                    ticks: { color: '#64748b', font: { size: 10 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    beginAtZero: true
                }
            }
        }
    });
}

function renderCategoryChart(categories) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;

    const labels = Object.keys(categories);
    const data = Object.values(categories);

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    const colors = ['#ef4444', '#f97316', '#eab308', '#3b82f6', '#a855f7', '#06b6d4', '#64748b'];

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { size: 10 }, boxWidth: 10 }
                }
            },
            cutout: '68%'
        }
    });
}

function renderHeatmap(cells) {
    const container = document.getElementById('heatmap-container');
    if (!container) return;

    const dayNames = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);

    let maxVal = Math.max(...cells.map(c => c.count), 1);

    let html = `
        <div class="min-w-[600px] grid grid-cols-25 gap-1 text-[10px]">
            <div class="col-span-1"></div>
            ${hours.map(h => `<div class="text-center text-slate-500 font-mono">${h}</div>`).join('')}
    `;

    for (let d = 0; d < 7; d++) {
        html += `<div class="font-bold text-slate-400 py-1">${dayNames[d]}</div>`;
        for (let h = 0; h < 24; h++) {
            const cell = cells.find(c => c.day_index === d && c.hour === h) || { count: 0 };
            const intensity = cell.count / maxVal;
            
            let bg = 'bg-slate-800/40';
            if (cell.count > 0) {
                if (intensity > 0.75) bg = 'bg-red-500 shadow-sm shadow-red-500/50';
                else if (intensity > 0.5) bg = 'bg-purple-600';
                else if (intensity > 0.25) bg = 'bg-indigo-600';
                else bg = 'bg-blue-900/80';
            }

            html += `
                <div class="heatmap-cell ${bg} flex items-center justify-center text-[9px] font-mono text-white/90 cursor-pointer" title="${dayNames[d]} ${h}:00 - ${cell.count} Entry">
                    ${cell.count > 0 ? cell.count : ''}
                </div>
            `;
        }
    }

    html += `</div>`;
    container.innerHTML = html;
}

function renderKeywords(keywords) {
    const container = document.getElementById('keywords-container');
    if (!container) return;

    if (keywords.length === 0) {
        container.innerHTML = `<span class="text-xs text-slate-500">Yeterli kelime verisi yok.</span>`;
        return;
    }

    container.innerHTML = keywords.map(k => `
        <span class="px-2.5 py-1 bg-dark-900 hover:bg-dark-700 border border-white/10 rounded-lg text-xs text-slate-300 hover:text-white transition-all cursor-default flex items-center gap-1.5">
            <span class="text-blue-400 font-mono">#</span>${escapeHtml(k.word)}
            <span class="text-[10px] bg-white/10 px-1.5 py-0.5 rounded text-slate-400 font-mono">${k.count}</span>
        </span>
    `).join('');
}

// ----------------- TAB 3: NETWORK GRAPH ----------------- //

async function loadNetwork() {
    const canvas = document.getElementById('networkCanvas');
    if (!canvas) return;

    try {
        const data = await fetchApi(`/api/coordination?days=${currentDays}`, `./data/coordination_${currentDays}.json`);
        networkDataCache = data.network;
        drawNetworkGraph(canvas, networkDataCache);
    } catch (err) {
        console.error("Failed to load network graph:", err);
    }
}

function drawNetworkGraph(canvas, networkData) {
    if (!networkData || !canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Set internal resolution
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = rect.width;
    const height = rect.height;

    const nodes = networkData.nodes.map((n, i) => {
        const angle = (i / networkData.nodes.length) * Math.PI * 2;
        const radius = Math.min(width, height) * 0.35;
        return {
            ...n,
            x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
            y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
            vx: 0,
            vy: 0
        };
    });

    const links = networkData.links;

    function render() {
        ctx.clearRect(0, 0, width, height);

        // Draw Links
        links.forEach(l => {
            const s = nodes.find(n => n.id === l.source);
            const t = nodes.find(n => n.id === l.target);
            if (!s || !t) return;

            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(t.x, t.y);
            ctx.strokeStyle = l.weight > 2 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(59, 130, 246, 0.2)';
            ctx.lineWidth = Math.min(5, 1 + l.weight);
            ctx.stroke();
        });

        // Draw Nodes
        nodes.forEach(n => {
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius || 12, 0, Math.PI * 2);
            ctx.fillStyle = n.coordinated > 0 ? '#ef4444' : '#3b82f6';
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#ffffff';
            ctx.stroke();

            // Label
            ctx.font = '10px Plus Jakarta Sans';
            ctx.fillStyle = '#f1f5f9';
            ctx.textAlign = 'center';
            ctx.fillText(`@${n.label}`, n.x, n.y + (n.radius || 12) + 12);
        });
    }

    render();
}

// ----------------- TAB 4: AUTHORS LIST ----------------- //

async function loadAuthors() {
    try {
        const data = await fetchApi(`/api/authors?days=${currentDays}`, `./data/authors_${currentDays}.json`);
        authorsDataCache = data.authors || [];

        // Populate author select filter dropdown in Entry Explorer
        const filterSelect = document.getElementById('entry-author-filter');
        if (filterSelect) {
            filterSelect.innerHTML = `<option value="">Tüm 27 Yazar</option>` +
                authorsDataCache.map(a => `<option value="${escapeHtml(a.nick)}">@${escapeHtml(a.nick)} (${a.period_entries || 0})</option>`).join('');
        }

        renderAuthorsGrid(authorsDataCache);
    } catch (err) {
        console.error("Failed to load authors:", err);
    }
}

function renderAuthorsGrid(authors) {
    const grid = document.getElementById('authors-grid');
    if (!grid) return;

    if (authors.length === 0) {
        grid.innerHTML = `<p class="text-slate-500 text-xs">Kayıtlı yazar bulunamadı.</p>`;
        return;
    }

    grid.innerHTML = authors.map(a => {
        const isHighRisk = (a.risk_score || 0) >= 50;
        const eksiProfileUrl = `https://eksisozluk.com/biri/${encodeURIComponent(a.nick)}`;
        
        return `
            <div class="glass-panel p-5 space-y-3 hover:border-white/20 transition-all group author-card" data-nick="${escapeHtml(a.nick.toLowerCase())}">
                <div class="flex items-start justify-between">
                    <div class="flex items-center space-x-3">
                        <div class="w-9 h-9 rounded-full ${isHighRisk ? 'bg-red-500/20 text-red-400 border-red-500/30' : 'bg-blue-500/20 text-blue-400 border-blue-500/30'} border flex items-center justify-center font-bold text-xs">
                            <i data-lucide="user" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h4 class="text-sm font-bold text-white group-hover:text-blue-400 transition-colors">
                                @${escapeHtml(a.nick)}
                            </h4>
                            <a href="${eksiProfileUrl}" target="_blank" class="text-[10px] text-slate-400 hover:text-blue-300 flex items-center gap-1">
                                <span>Profili Aç</span>
                                <i data-lucide="external-link" class="w-2.5 h-2.5"></i>
                            </a>
                        </div>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isHighRisk ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}">
                        ${a.risk_score || 0}% RİSK
                    </span>
                </div>

                <!-- Stats summary -->
                <div class="grid grid-cols-2 gap-2 text-center bg-dark-900/60 rounded-lg p-2 text-xs">
                    <div>
                        <span class="text-[10px] text-slate-400 block">Bu Hafta</span>
                        <span class="font-bold text-white font-mono">${a.period_entries || 0} entry</span>
                    </div>
                    <div>
                        <span class="text-[10px] text-slate-400 block">Koordineli</span>
                        <span class="font-bold text-red-400 font-mono">${a.coordinated_entries || 0} operasyon</span>
                    </div>
                </div>

                <!-- Top Topics -->
                <div class="space-y-1">
                    <span class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Son Odak Konuları:</span>
                    <div class="flex flex-wrap gap-1">
                        ${(a.top_topics && a.top_topics.length > 0) ? a.top_topics.map(t => `
                            <span class="text-[10px] bg-dark-900 text-slate-300 px-2 py-0.5 rounded border border-white/5 truncate max-w-full">
                                ${escapeHtml(t)}
                            </span>
                        `).join('') : '<span class="text-[10px] text-slate-500">Kayıt yok</span>'}
                    </div>
                </div>

                <!-- Action Button -->
                <button onclick="openAuthorModal('${escapeHtml(a.nick)}')" class="w-full py-1.5 bg-dark-900 hover:bg-dark-700 border border-white/10 text-slate-300 hover:text-white rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5">
                    <i data-lucide="file-search" class="w-3.5 h-3.5 text-blue-400"></i>
                    <span>Yazar Dosyasını İncele</span>
                </button>
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

function filterAuthorCards() {
    const term = (document.getElementById('author-search-input').value || '').toLowerCase();
    document.querySelectorAll('.author-card').forEach(card => {
        const nick = card.getAttribute('data-nick') || '';
        if (nick.includes(term)) {
            card.classList.remove('hidden');
        } else {
            card.classList.add('hidden');
        }
    });
}

// ----------------- TAB 5: ENTRY EXPLORER ----------------- //

async function loadEntries() {
    const search = document.getElementById('entry-search-input')?.value || '';
    const category = document.getElementById('entry-category-filter')?.value || '';
    const author = document.getElementById('entry-author-filter')?.value || '';
    const coordinatedOnly = document.getElementById('entry-coordinated-toggle')?.checked || false;

    const params = new URLSearchParams({
        days: currentDays,
        limit: entryLimit,
        offset: entryOffset
    });

    if (search) params.append('search', search);
    if (category && category !== 'Tümü') params.append('category', category);
    if (author) params.append('author', author);
    if (coordinatedOnly) params.append('coordinated_only', 'true');

    const container = document.getElementById('entries-container');
    container.innerHTML = `
        <div class="glass-panel p-6 text-center text-slate-400">
            <div class="inline-block animate-spin mb-2 text-blue-400"><i data-lucide="loader-2" class="w-6 h-6"></i></div>
            <p>Entryler filtreleniyor...</p>
        </div>
    `;
    lucide.createIcons();

    try {
        const data = await fetchApi(`/api/entries?${params.toString()}`, `./data/entries_${currentDays}.json`);
        totalEntriesCount = data.total || 0;
        let entries = data.entries || [];

        // In static fallback mode, perform client-side filtering if parameters are applied
        if (search || (category && category !== 'Tümü') || author || coordinatedOnly) {
            entries = entries.filter(e => {
                if (search && !(e.topic.toLowerCase().includes(search.toLowerCase()) || e.content.toLowerCase().includes(search.toLowerCase()))) return false;
                if (category && category !== 'Tümü' && e.category !== category) return false;
                if (author && e.author !== author) return false;
                if (coordinatedOnly && !e.is_coordinated) return false;
                return true;
            });
            totalEntriesCount = entries.length;
        }

        document.getElementById('entries-count-label').innerText = `${totalEntriesCount} entry arasından ${entryOffset + 1} - ${Math.min(entryOffset + entryLimit, totalEntriesCount)} gösteriliyor`;

        document.getElementById('btn-prev-page').disabled = entryOffset === 0;
        document.getElementById('btn-next-page').disabled = (entryOffset + entryLimit) >= totalEntriesCount;

        if (entries.length === 0) {
            container.innerHTML = `
                <div class="glass-panel p-8 text-center text-slate-400">
                    <i data-lucide="file-question" class="w-8 h-8 mx-auto mb-2 text-slate-500"></i>
                    <p>Arama kriterlerine uygun entry bulunamadı.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        container.innerHTML = entries.map(e => `
            <div class="glass-panel p-4 space-y-2.5 hover:border-white/20 transition-all ${e.is_coordinated ? 'border-l-4 border-red-500' : ''}">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex items-center space-x-2">
                        <button onclick="openAuthorModal('${escapeHtml(e.author)}')" class="font-bold text-xs text-blue-400 hover:underline">
                            @${escapeHtml(e.author)}
                        </button>
                        <span class="text-slate-600">•</span>
                        <span class="px-2 py-0.5 bg-dark-900 text-slate-300 border border-white/5 rounded text-[10px] font-semibold">
                            ${escapeHtml(e.category)}
                        </span>
                        ${e.is_coordinated ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30 rounded text-[10px] font-bold">KOORDİNELİ</span>' : ''}
                    </div>
                    <span class="text-slate-400 font-mono text-[11px]">${e.date_str || e.created_at.replace('T', ' ').substring(0, 16)}</span>
                </div>

                <div>
                    <h4 class="text-sm font-bold text-white hover:text-blue-300 transition-colors">
                        <a href="https://eksisozluk.com/?q=${encodeURIComponent(e.topic)}" target="_blank" class="flex items-center gap-1">
                            <span># ${escapeHtml(e.topic)}</span>
                            <i data-lucide="external-link" class="w-3 h-3 text-slate-500"></i>
                        </a>
                    </h4>
                    <p class="text-xs text-slate-300 mt-1.5 leading-relaxed bg-dark-900/40 p-3 rounded-lg border border-white/5">
                        ${escapeHtml(e.content)}
                    </p>
                </div>

                <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                    <a href="https://eksisozluk.com/entry/${e.id}" target="_blank" class="hover:text-blue-400 font-mono">
                        Ekşi Entry #${e.id}
                    </a>
                    <div class="flex items-center space-x-3">
                        <span>❤️ ${e.favorite_count || 0}</span>
                        <span>💬 ${e.comment_count || 0}</span>
                    </div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load entries:", err);
    }
}

function prevPage() {
    if (entryOffset >= entryLimit) {
        entryOffset -= entryLimit;
        loadEntries();
    }
}

function nextPage() {
    if (entryOffset + entryLimit < totalEntriesCount) {
        entryOffset += entryLimit;
        loadEntries();
    }
}

// ----------------- AUTHOR DOSSIER MODAL ----------------- //

async function openAuthorModal(nick) {
    const modal = document.getElementById('author-modal');
    modal.classList.remove('hidden');

    document.getElementById('modal-author-nick').innerText = `@${nick}`;
    document.getElementById('modal-author-eksilink').href = `https://eksisozluk.com/biri/${encodeURIComponent(nick)}`;

    const body = document.getElementById('modal-author-body');
    body.innerHTML = `<div class="text-center p-6 text-slate-400"><i data-lucide="loader-2" class="w-6 h-6 animate-spin mx-auto mb-2 text-blue-400"></i> Yazar verileri yükleniyor...</div>`;
    lucide.createIcons();

    try {
        const res = await fetch(`/api/entries?author=${encodeURIComponent(nick)}&days=30&limit=30`);
        const data = await res.json();
        const entries = data.entries || [];

        let html = `
            <div class="space-y-4">
                <div class="grid grid-cols-3 gap-2 bg-dark-900 p-3 rounded-xl border border-white/5 text-center">
                    <div>
                        <span class="text-slate-400 block text-[10px]">İncelenen Entry</span>
                        <span class="text-sm font-bold text-white">${entries.length}</span>
                    </div>
                    <div>
                        <span class="text-slate-400 block text-[10px]">Koordineli Oranı</span>
                        <span class="text-sm font-bold text-red-400">${entries.filter(e => e.is_coordinated).length} entry</span>
                    </div>
                    <div>
                        <span class="text-slate-400 block text-[10px]">Durum</span>
                        <span class="text-sm font-bold text-emerald-400">İzleniyor</span>
                    </div>
                </div>

                <h4 class="font-bold text-slate-200 uppercase tracking-wider text-[11px]">Son Paylaşımları & Hedef Başlıklar</h4>
                <div class="space-y-2 max-h-[350px] overflow-y-auto pr-1">
                    ${entries.map(e => `
                        <div class="p-3 bg-dark-900/90 rounded-lg border border-white/5 space-y-1.5">
                            <div class="flex items-center justify-between text-[11px]">
                                <span class="font-bold text-white"># ${escapeHtml(e.topic)}</span>
                                <span class="text-slate-400 font-mono">${e.date_str || e.created_at.substring(0, 10)}</span>
                            </div>
                            <p class="text-slate-300 italic">"${escapeHtml(e.content)}"</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        body.innerHTML = html;
        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load author dossier:", err);
    }
}

function closeAuthorModal() {
    document.getElementById('author-modal').classList.add('hidden');
}

// ----------------- LIVE SCRAPER MODAL ----------------- //

function openScrapeModal() {
    document.getElementById('scrape-modal').classList.remove('hidden');
    document.getElementById('scrape-pre-form').classList.remove('hidden');
    document.getElementById('scrape-progress-panel').classList.add('hidden');
}

function closeScrapeModal() {
    document.getElementById('scrape-modal').classList.add('hidden');
    if (scrapePollTimer) {
        clearInterval(scrapePollTimer);
        scrapePollTimer = null;
    }
}

async function triggerLiveScrape() {
    const days = parseInt(document.getElementById('scrape-days-select').value || '7');
    document.getElementById('scrape-pre-form').classList.add('hidden');
    document.getElementById('scrape-progress-panel').classList.remove('hidden');

    const logsContainer = document.getElementById('scrape-terminal-logs');
    logsContainer.innerHTML = `<div class="text-blue-400">[*] Canlı tarama görevi başlatılıyor (27 yazar)...</div>`;

    try {
        const res = await fetch(`/api/scrape/start?days=${days}`, { method: 'POST' });
        const data = await res.json();
        activeScrapeJobId = data.job_id;

        scrapePollTimer = setInterval(() => pollScrapeProgress(activeScrapeJobId), 1500);
    } catch (err) {
        logsContainer.innerHTML += `<div class="text-red-400">Tarama başlatılamadı: ${err}</div>`;
    }
}

async function pollScrapeProgress(jobId) {
    try {
        const res = await fetch(`/api/scrape/status/${jobId}`);
        const data = await res.json();

        const logsContainer = document.getElementById('scrape-terminal-logs');
        const progressBar = document.getElementById('scrape-progress-bar');
        const statusText = document.getElementById('scrape-status-text');
        const percentText = document.getElementById('scrape-percent-text');

        const processed = data.processed || data.authors_processed || 0;
        const total = data.total || data.total_authors || 27;
        const percent = Math.min(100, Math.round((processed / total) * 100));

        progressBar.style.width = `${percent}%`;
        percentText.innerText = `${percent}%`;
        statusText.innerText = data.current ? `İşleniyor: ${data.current}` : 'Taranıyor...';

        if (data.logs && Array.isArray(data.logs)) {
            logsContainer.innerHTML = data.logs.map(l => {
                const color = l.type === 'success' ? 'text-emerald-400' : (l.type === 'error' ? 'text-red-400' : 'text-slate-300');
                return `<div class="${color}">[${l.time}] ${escapeHtml(l.msg)}</div>`;
            }).join('');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }

        if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(scrapePollTimer);
            scrapePollTimer = null;
            statusText.innerText = data.status === 'completed' ? 'Tarama başarıyla tamamlandı!' : 'Tarama tamamlandı (uyarılar var).';
            
            // Refresh data in UI
            setTimeout(() => {
                loadOverviewStats();
                loadNarrativeBriefing();
                loadAuthors();
                if (currentTab === 'analytics') loadAnalytics();
                if (currentTab === 'network') loadNetwork();
                if (currentTab === 'entries') loadEntries();
            }, 1000);
        }
    } catch (err) {
        console.error("Poll error:", err);
    }
}

// ----------------- UTILS ----------------- //

function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
