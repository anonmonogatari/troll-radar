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
    const isStaticHost = window.location.hostname.includes('github.io') || window.location.protocol === 'file:';
    
    if (isStaticHost && fallbackStaticPath) {
        try {
            const staticRes = await fetch(fallbackStaticPath);
            if (staticRes.ok) {
                return await staticRes.json();
            }
        } catch (e) {
            console.warn("Static fetch fallback:", e);
        }
    }

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
    loadDiscovery();
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
    ['briefing', 'discovery', 'analytics', 'network', 'authors', 'entries'].forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) {
            if (v === tabId) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });

    if (tabId === 'discovery') {
        loadDiscovery();
    } else if (tabId === 'analytics') {
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

// ----------------- TAB 0: AUTOMATED DISCOVERY & SCORING ----------------- //

async function loadDiscovery() {
    const cellsGrid = document.getElementById('discovery-cells-grid');
    const tbody = document.getElementById('discovery-candidates-tbody');

    if (cellsGrid && cellsGrid.innerHTML.trim() === '') {
        cellsGrid.innerHTML = `
            <div class="col-span-3 glass-panel p-6 text-center text-slate-400">
                <div class="inline-block animate-spin mb-2 text-purple-400"><i data-lucide="loader-2" class="w-6 h-6"></i></div>
                <p>Troll hücreleri analiz ediliyor...</p>
            </div>
        `;
    }
    if (tbody && tbody.innerHTML.trim() === '') {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-slate-400"><div class="inline-block animate-spin mb-2 text-purple-400"><i data-lucide="loader-2" class="w-5 h-5"></i></div><p>Aday hesaplar değerlendiriliyor...</p></td></tr>`;
    }
    lucide.createIcons();

    try {
        const data = await fetchApi(`/api/discovery/candidates?days=${currentDays}`, `./data/discovery_${currentDays}.json`);
        renderDiscoveryCells(data.cells || []);
        renderDiscoveryCandidates(data.candidates || []);
    } catch (err) {
        console.error("Failed to load discovery data:", err);
        if (cellsGrid) cellsGrid.innerHTML = `<div class="col-span-3 text-center text-slate-500 text-xs py-4">Veri yüklenemedi.</div>`;
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-slate-500 text-xs">Aday verisi alınamadı.</td></tr>`;
    }
}

function renderDiscoveryCells(cells) {
    const grid = document.getElementById('discovery-cells-grid');
    if (!grid) return;

    if (cells.length === 0) {
        grid.innerHTML = `<p class="text-xs text-slate-500 col-span-3 text-center py-4">Henüz belirgin bir troll hücresi ayrışmadı.</p>`;
        return;
    }

    grid.innerHTML = cells.map(c => `
        <div class="bg-dark-900/80 border border-purple-500/20 rounded-xl p-4 space-y-3 hover:border-purple-500/40 transition-all">
            <div class="flex items-start justify-between">
                <div>
                    <span class="text-[10px] uppercase font-bold text-purple-400 tracking-wider">Hücre Grubu</span>
                    <h4 class="text-sm font-bold text-white">${escapeHtml(c.cell_name)}</h4>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                    Ort. %${c.average_troll_score}
                </span>
            </div>

            <div class="text-xs text-slate-300">
                <span class="text-[11px] text-slate-400 block mb-1">Dahil Olan Hesaplar (${c.member_count}):</span>
                <div class="flex flex-wrap gap-1">
                    ${c.members.map(m => `
                        <button onclick="openAuthorModal('${escapeHtml(m)}')" class="px-2 py-0.5 bg-dark-800 border border-white/5 rounded text-[10px] text-purple-300 hover:text-white font-mono">
                            @${escapeHtml(m)}
                        </button>
                    `).join('')}
                </div>
            </div>

            <div class="border-t border-white/5 pt-2 text-[11px] text-slate-400">
                <span class="block text-[10px] text-slate-500">Hedef Başlıklar:</span>
                <p class="truncate text-slate-300 mt-0.5">${c.top_evidence_topics.slice(0, 2).map(t => '#' + escapeHtml(t)).join(', ')}</p>
            </div>
        </div>
    `).join('');

    lucide.createIcons();
}

function renderDiscoveryCandidates(candidates) {
    const tbody = document.getElementById('discovery-candidates-tbody');
    if (!tbody) return;

    if (candidates.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-slate-500">Aday hesap bulunamadı.</td></tr>`;
        return;
    }

    tbody.innerHTML = candidates.map(c => {
        const score = c.troll_score || 0;
        let barColor = 'bg-slate-700';
        let badgeBg = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
        
        if (score >= 70) {
            barColor = 'bg-red-500';
            badgeBg = 'bg-red-500/20 text-red-400 border-red-500/30';
        } else if (score >= 50) {
            barColor = 'bg-orange-500';
            badgeBg = 'bg-orange-500/20 text-orange-400 border-orange-500/30';
        } else if (score >= 30) {
            barColor = 'bg-yellow-500';
            badgeBg = 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
        }

        const m = c.metrics || {};
        const isOrganic = score === 0 || c.risk_level === 'Organik';

        return `
            <tr class="hover:bg-white/[0.03] transition-colors border-b border-white/5">
                <td class="py-3 px-3 whitespace-nowrap">
                    <button onclick="openAuthorModal('${escapeHtml(c.nick)}')" class="font-bold text-white hover:text-blue-400 font-mono text-xs flex items-center gap-1.5 transition-colors">
                        <i data-lucide="user" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
                        <span class="truncate max-w-[170px]" title="@${escapeHtml(c.nick)}">@${escapeHtml(c.nick)}</span>
                    </button>
                </td>
                <td class="py-3 px-3 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                        <div class="w-14 bg-dark-900 rounded-full h-1.5 overflow-hidden border border-white/5">
                            <div class="${barColor} h-1.5 rounded-full" style="width: ${score}%"></div>
                        </div>
                        <span class="font-bold font-mono ${isOrganic ? 'text-slate-400' : 'text-white'} text-[11px]">%${score}</span>
                    </div>
                    <span class="text-[9px] px-1.5 py-0.5 rounded border ${badgeBg} inline-block mt-1 font-semibold whitespace-nowrap">
                        ${escapeHtml(c.risk_level)}
                    </span>
                </td>
                <td class="py-3 px-3 whitespace-nowrap">
                    <span class="px-2 py-0.5 ${isOrganic ? 'bg-slate-800 text-slate-400 border-white/5' : 'bg-purple-500/15 text-purple-300 border-purple-500/25'} border rounded text-[10px] font-semibold inline-block">
                        ${escapeHtml(c.detected_cell)}
                    </span>
                </td>
                <td class="py-3 px-3 font-mono ${m.inception_count > 0 ? 'text-purple-300 font-bold' : 'text-slate-500'} whitespace-nowrap">
                    ${m.inception_count || 0} başlık
                </td>
                <td class="py-3 px-3 font-mono ${m.early_swarm_count > 0 ? 'text-red-300 font-semibold' : 'text-slate-500'} whitespace-nowrap">
                    ${m.early_swarm_count || 0} entry <span class="text-[10px] text-slate-500">(%${m.manufactured_focus_ratio || 0})</span>
                </td>
                <td class="py-3 px-3 font-mono ${m.vote_brigading > 0 ? 'text-amber-300 font-semibold' : 'text-slate-500'} whitespace-nowrap">
                    %${m.vote_brigading || 0}
                </td>
                <td class="py-3 px-3 font-mono ${m.stance_alignment > 0 ? 'text-blue-300 font-semibold' : 'text-slate-500'} whitespace-nowrap">
                    %${m.stance_alignment || 0}
                </td>
                <td class="py-3 px-3 text-right whitespace-nowrap">
                    ${c.is_monitored ? `
                        <button onclick="unpromoteCandidate('${escapeHtml(c.nick)}')" class="px-2.5 py-1 bg-red-500/15 hover:bg-red-500/25 border border-red-500/35 text-red-400 hover:text-red-300 rounded text-[10px] font-bold transition-all inline-flex items-center gap-1">
                            <i data-lucide="user-minus" class="w-3 h-3"></i>
                            <span>İzlemeden Çıkar</span>
                        </button>
                    ` : `
                        <button onclick="promoteCandidate('${escapeHtml(c.nick)}')" class="px-2.5 py-1 bg-dark-900 hover:bg-dark-700 border border-white/10 text-blue-400 hover:text-white rounded text-[10px] font-semibold transition-all inline-flex items-center gap-1">
                            <i data-lucide="user-plus" class="w-3 h-3"></i>
                            <span>+ İzlemeye Al</span>
                        </button>
                    `}
                </td>
            </tr>
        `;
    }).join('');

    lucide.createIcons();
}

async function triggerDiscoveryScan() {
    const btn = document.getElementById('discovery-scan-btn');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Gündem Taranıyor...</span>`;
        lucide.createIcons();
    }

    try {
        const isStatic = window.location.hostname.includes('github.io');
        if (!isStatic) {
            await fetch(`/api/discovery/scan?days=${currentDays}&live_gundem=true`, { method: 'POST' });
        }
        await loadDiscovery();
    } catch (e) {
        console.error("Scan error:", e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            lucide.createIcons();
        }
    }
}

async function promoteCandidate(nick) {
    try {
        const isStatic = window.location.hostname.includes('github.io');
        if (!isStatic) {
            await fetch(`/api/discovery/promote/${encodeURIComponent(nick)}`, { method: 'POST' });
        }
        await loadAuthors();
        await loadDiscovery();
    } catch (e) {
        console.error("Promote error:", e);
    }
}

async function unpromoteCandidate(nick) {
    try {
        const isStatic = window.location.hostname.includes('github.io');
        if (!isStatic) {
            await fetch(`/api/discovery/unpromote/${encodeURIComponent(nick)}`, { method: 'POST' });
        }
        await loadAuthors();
        await loadDiscovery();
    } catch (e) {
        console.error("Unpromote error:", e);
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

                    <!-- Chronological Sample Entry Quotes (Asynchronous Masonry Layout) -->
                    <div class="space-y-2 mt-3 pt-3 border-t border-white/5">
                        <h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tespit Edilen Koordineli Entry Alıntıları:</h4>
                        <div class="columns-1 md:columns-2 gap-3">
                            ${n.sample_entries.map(s => `
                                <div class="break-inside-avoid mb-3 bg-dark-900/80 border border-white/5 rounded-xl p-3.5 space-y-2 hover:border-white/15 transition-all">
                                    <div class="flex items-center justify-between text-[11px]">
                                        <button onclick="openAuthorModal('${escapeHtml(s.author)}')" class="font-bold text-blue-400 hover:underline">
                                            @${escapeHtml(s.author)}
                                        </button>
                                        <span class="text-slate-400 font-mono text-[10px]">${s.date_str || s.created_at.replace('T', ' ').substring(0, 16)}</span>
                                    </div>
                                    <p class="text-xs text-slate-300 italic leading-relaxed">
                                        "${escapeHtml(s.content)}"
                                    </p>
                                    <div class="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-white/5">
                                        <a href="https://eksisozluk.com/entry/${s.id}" target="_blank" class="hover:text-blue-300 font-mono">#${s.id}</a>
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
    const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));

    let maxVal = Math.max(...cells.map(c => c.count), 1);

    let html = `
        <div class="heatmap-wrapper">
            <div class="heatmap-grid text-[10px]">
                <!-- Top-Left Corner Header -->
                <div class="text-[10px] text-slate-500 font-bold uppercase tracking-wider text-center">Gün</div>
                
                <!-- 24 Hour Column Headers -->
                ${hours.map(h => `
                    <div class="text-center text-slate-400 font-mono text-[10px] py-1 select-none font-semibold">${h}</div>
                `).join('')}
    `;

    for (let d = 0; d < 7; d++) {
        html += `
            <div class="font-bold text-slate-300 font-mono text-[11px] py-1 text-center bg-dark-900/80 rounded border border-white/5 select-none">
                ${dayNames[d]}
            </div>
        `;

        for (let h = 0; h < 24; h++) {
            const cell = cells.find(c => c.day_index === d && c.hour === h) || { count: 0 };
            const intensity = cell.count / maxVal;
            
            let bg = 'bg-slate-900/60 text-slate-600';
            if (cell.count > 0) {
                if (intensity >= 0.75) bg = 'bg-red-500 text-white font-bold shadow-md shadow-red-500/30';
                else if (intensity >= 0.50) bg = 'bg-purple-600 text-white font-semibold shadow-sm shadow-purple-600/20';
                else if (intensity >= 0.25) bg = 'bg-indigo-600 text-white font-medium';
                else bg = 'bg-blue-900/90 text-blue-200 font-medium';
            }

            html += `
                <div class="heatmap-cell ${bg} flex items-center justify-center text-[10px] font-mono select-none cursor-pointer" 
                     title="${dayNames[d]} ${String(h).padStart(2, '0')}:00 - Toplam ${cell.count} Entry">
                    ${cell.count > 0 ? cell.count : ''}
                </div>
            `;
        }
    }

    html += `
            </div>
        </div>
    `;
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

// ----------------- TAB 3: NETWORK GRAPH (CLEAN CIRCULAR ORBITAL RADAR) ----------------- //

let networkMinWeight = 1; // Show all connections cleanly with ultra-thin curved lines

function setNetworkMinWeight(weight) {
    networkMinWeight = weight;
    [1, 2, 3].forEach(w => {
        const btn = document.getElementById(`net-btn-w${w}`);
        if (btn) {
            if (w === weight) {
                btn.className = "px-2 py-1 rounded text-[11px] font-semibold transition-all bg-blue-600 text-white shadow";
            } else {
                btn.className = "px-2 py-1 rounded text-[11px] font-semibold transition-all text-slate-400 hover:text-white";
            }
        }
    });
    const canvas = document.getElementById('networkCanvas');
    if (canvas && networkDataCache) {
        drawNetworkGraph(canvas, networkDataCache);
    }
}

function resetNetworkPhysics() {
    const canvas = document.getElementById('networkCanvas');
    if (canvas && networkDataCache) {
        drawNetworkGraph(canvas, networkDataCache);
    }
}

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

let activeNetworkAnimation = null;

function drawNetworkGraph(canvas, networkData) {
    if (!networkData || !canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Stop any existing animation loop
    if (activeNetworkAnimation && activeNetworkAnimation.stop) {
        activeNetworkAnimation.stop();
    }

    // Set High-DPI Resolution
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(width * 0.35, height * 0.38 - 35);

    // Sort nodes to cluster active coordinators next to each other along the ring
    const rawNodes = [...networkData.nodes].sort((a, b) => (b.coordinated || 0) - (a.coordinated || 0));
    const totalNodes = rawNodes.length;

    // Filter active links based on min weight
    const allLinks = networkData.links || [];
    const activeLinks = allLinks.filter(l => l.weight >= networkMinWeight);

    // Calculate node positions along the clean circular radar ring
    const nodes = rawNodes.map((n, i) => {
        const angle = (i / totalNodes) * Math.PI * 2 - Math.PI / 2;
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius;

        let dotColor = '#3b82f6';
        let dotRadius = 5.5;
        if (n.coordinated >= 5) {
            dotColor = '#ef4444';
            dotRadius = 7.5;
        } else if (n.coordinated >= 2) {
            dotColor = '#f59e0b';
            dotRadius = 6.5;
        }

        return {
            ...n,
            x: x,
            y: y,
            angle: angle,
            dotRadius: dotRadius,
            dotColor: dotColor,
            isHub: n.coordinated >= 4
        };
    });

    // Build fast lookup maps
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const neighborMap = new Map();
    nodes.forEach(n => neighborMap.set(n.id, new Set()));
    activeLinks.forEach(l => {
        if (neighborMap.has(l.source)) neighborMap.get(l.source).add(l.target);
        if (neighborMap.has(l.target)) neighborMap.get(l.target).add(l.source);
    });

    let hoveredNode = null;
    let radarAngle = 0;
    let animId = null;

    function render() {
        ctx.clearRect(0, 0, width, height);

        // 1. Draw Subtle Radar Background Rings
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
        ctx.lineWidth = 1;
        [0.35, 0.70, 1.0].forEach(factor => {
            ctx.beginPath();
            ctx.arc(cx, cy, radius * factor, 0, Math.PI * 2);
            ctx.stroke();
        });

        // Radar Crosshairs
        ctx.beginPath();
        ctx.moveTo(cx - radius * 1.05, cy); ctx.lineTo(cx + radius * 1.05, cy);
        ctx.moveTo(cx, cy - radius * 1.05); ctx.lineTo(cx, cy + radius * 1.05);
        ctx.stroke();

        // 2. Fast Sweeping Radar Scan Line
        radarAngle += 0.025;
        if (radarAngle > Math.PI * 2) radarAngle -= Math.PI * 2;
        
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, radius * 1.02, radarAngle - 0.25, radarAngle);
        ctx.closePath();
        const sweepGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        sweepGrad.addColorStop(0, 'rgba(56, 189, 248, 0.0)');
        sweepGrad.addColorStop(1, 'rgba(56, 189, 248, 0.06)');
        ctx.fillStyle = sweepGrad;
        ctx.fill();
        ctx.restore();

        const isHoverActive = !!hoveredNode;
        const activeNeighbors = isHoverActive ? neighborMap.get(hoveredNode.id) : null;

        // 3. Draw Ultra-Thin Curved Links (Quadratic Bezier Curves toward Center)
        activeLinks.forEach(l => {
            const s = nodeMap.get(l.source);
            const t = nodeMap.get(l.target);
            if (!s || !t) return;

            const isConnected = isHoverActive && (s.id === hoveredNode.id || t.id === hoveredNode.id);
            
            // Curve gently bends towards center (0.45 strength)
            const cpx = cx * 0.45 + (s.x + t.x) * 0.275;
            const cpy = cy * 0.45 + (s.y + t.y) * 0.275;

            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.quadraticCurveTo(cpx, cpy, t.x, t.y);

            if (isHoverActive) {
                if (isConnected) {
                    ctx.strokeStyle = '#38bdf8';
                    ctx.lineWidth = Math.min(2.5, 1.2 + l.weight * 0.3);
                    ctx.shadowColor = '#38bdf8';
                    ctx.shadowBlur = 8;
                    ctx.stroke();
                    ctx.shadowBlur = 0;
                }
            } else {
                ctx.lineWidth = 0.6; // Ultra thin hairline!
                if (l.weight >= 3) {
                    ctx.strokeStyle = 'rgba(239, 68, 68, 0.22)';
                } else if (l.weight >= 2) {
                    ctx.strokeStyle = 'rgba(245, 158, 11, 0.16)';
                } else {
                    ctx.strokeStyle = 'rgba(59, 130, 246, 0.08)';
                }
                ctx.stroke();
            }
        });

        // 4. Draw Clean Orbital Nodes
        nodes.forEach(n => {
            const isHovered = isHoverActive && hoveredNode.id === n.id;
            const isNeighbor = activeNeighbors && activeNeighbors.has(n.id);
            const isDimmed = isHoverActive && !isHovered && !isNeighbor;

            ctx.save();
            if (isDimmed) {
                ctx.globalAlpha = 0.22;
            } else {
                ctx.globalAlpha = 1.0;
            }

            // Draw Node Circle
            const curRadius = isHovered ? n.dotRadius + 3 : n.dotRadius;
            
            if (isHovered || (n.isHub && !isDimmed)) {
                ctx.shadowColor = n.dotColor;
                ctx.shadowBlur = isHovered ? 14 : 8;
            }

            ctx.beginPath();
            ctx.arc(n.x, n.y, curRadius, 0, Math.PI * 2);
            ctx.fillStyle = isHovered ? '#38bdf8' : n.dotColor;
            ctx.fill();

            ctx.lineWidth = isHovered ? 2.5 : 1.5;
            ctx.strokeStyle = isHovered ? '#ffffff' : (isNeighbor ? '#38bdf8' : 'rgba(255, 255, 255, 0.5)');
            ctx.stroke();
            ctx.shadowBlur = 0;

            // 5. Radial Outward Label Alignment (Never Overlaps!)
            const cosA = Math.cos(n.angle);
            const sinA = Math.sin(n.angle);
            const labelOffset = curRadius + 7;
            const lx = n.x + cosA * labelOffset;
            const ly = n.y + sinA * labelOffset + 3;

            ctx.font = isHovered ? 'bold 11px Plus Jakarta Sans' : (n.isHub ? '600 10px Plus Jakarta Sans' : '10px Plus Jakarta Sans');
            
            if (cosA > 0.25) {
                ctx.textAlign = 'left';
            } else if (cosA < -0.25) {
                ctx.textAlign = 'right';
            } else {
                ctx.textAlign = 'center';
            }

            ctx.fillStyle = isHovered ? '#ffffff' : (isNeighbor ? '#38bdf8' : (n.isHub ? '#fca5a5' : '#94a3b8'));
            ctx.fillText(`@${n.label}`, lx, ly);

            ctx.restore();
        });

        // 6. Sleek Minimalist Center Radar HUD on Hover
        if (hoveredNode) {
            const peers = activeLinks
                .filter(l => l.source === hoveredNode.id || l.target === hoveredNode.id)
                .map(l => {
                    const peerId = l.source === hoveredNode.id ? l.target : l.source;
                    return { nick: peerId, weight: l.weight };
                })
                .sort((a, b) => b.weight - a.weight);

            const cardW = 220;
            const cardH = 82;
            const hx = cx - cardW / 2;
            const hy = cy - cardH / 2;

            // Frosted Center HUD
            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(hx, hy, cardW, cardH, 12);
            ctx.fill();
            ctx.stroke();

            // Text info
            ctx.textAlign = 'center';
            ctx.fillStyle = '#38bdf8';
            ctx.font = 'bold 12px Plus Jakarta Sans';
            ctx.fillText(`@${hoveredNode.label}`, cx, hy + 22);

            ctx.fillStyle = '#f1f5f9';
            ctx.font = '10px Plus Jakarta Sans';
            ctx.fillText(`${hoveredNode.entries || 0} Entry • ${hoveredNode.coordinated || 0} Koordineli Operasyon`, cx, hy + 42);

            ctx.fillStyle = '#94a3b8';
            ctx.font = '9px Plus Jakarta Sans';
            const peerStr = peers.length > 0 
                ? `Ortaklar: ${peers.slice(0, 2).map(p => `@${p.nick} (${p.weight}x)`).join(', ')}`
                : 'Tekil / Ayrık Hücre';
            ctx.fillText(peerStr, cx, hy + 62);
        }
    }

    function animLoop() {
        render();
        animId = requestAnimationFrame(animLoop);
    }

    animLoop();

    activeNetworkAnimation = {
        stop: () => {
            if (animId) cancelAnimationFrame(animId);
        }
    };

    function getMousePos(evt) {
        const r = canvas.getBoundingClientRect();
        return {
            x: evt.clientX - r.left,
            y: evt.clientY - r.top
        };
    }

    function findNodeAt(pos) {
        return nodes.find(n => {
            const dx = n.x - pos.x;
            const dy = n.y - pos.y;
            return Math.sqrt(dx * dx + dy * dy) <= (n.dotRadius + 9);
        });
    }

    // Fast Responsive Hover & Click
    canvas.onmousemove = (e) => {
        const pos = getMousePos(e);
        const prev = hoveredNode;
        hoveredNode = findNodeAt(pos);
        if (prev !== hoveredNode) {
            canvas.style.cursor = hoveredNode ? 'pointer' : 'default';
        }
    };

    canvas.onmouseleave = () => {
        hoveredNode = null;
        canvas.style.cursor = 'default';
    };

    canvas.onclick = (e) => {
        const pos = getMousePos(e);
        const clicked = findNodeAt(pos);
        if (clicked) {
            openAuthorModal(clicked.id);
        }
    };
}

// Global Window Resize Listener to Keep Network Graph Sharp & Centered
let resizeTimeout = null;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (currentTab === 'network' && networkDataCache) {
            const canvas = document.getElementById('networkCanvas');
            if (canvas) drawNetworkGraph(canvas, networkDataCache);
        }
    }, 250);
});

// Export Dropdown Handlers (Click-to-toggle with safe menu navigation)
function toggleExportMenu(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('export-dropdown');
    if (!dropdown) return;
    dropdown.classList.toggle('hidden');
    lucide.createIcons();
}

function closeExportMenu() {
    const dropdown = document.getElementById('export-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
    }
}

async function downloadExport(format) {
    closeExportMenu();
    
    // In local server mode with active backend
    if (isServerOnline) {
        try {
            const res = await fetch(`/api/export?format=${format}&days=${currentDays}`);
            if (!res.ok) throw new Error("Export fetch failed");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = format === 'csv' 
                ? `troll_radar_istihbarat_raporu_${currentDays}d.csv`
                : `troll_radar_istihbarat_bulteni_${currentDays}d.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            return;
        } catch (e) {
            console.warn("Backend export fetch fallback:", e);
        }
    }

    // In static GitHub Pages mode (construct rich export bundle client-side)
    try {
        const stats = await fetchApi(`/api/stats?days=${currentDays}`, `./data/stats_${currentDays}.json`);
        const narrativesData = await fetchApi(`/api/narratives?days=${currentDays}`, `./data/narratives_${currentDays}.json`);
        const authorsData = await fetchApi(`/api/authors?days=${currentDays}`, `./data/authors_${currentDays}.json`);
        const entriesData = await fetchApi(`/api/entries?days=${currentDays}&limit=2000`, `./data/entries_${currentDays}.json`);
        
        const narratives = narrativesData.narratives || [];
        const authors = authorsData.authors || [];
        const entries = entriesData.entries || [];

        if (format === 'json') {
            const bundle = {
                rapor_basligi: "TrollRadar // Ekşi Sözlük İstihbarat ve Manipülasyon Raporu",
                olusturulma_tarihi: new Date().toISOString(),
                analiz_periyodu_gun: currentDays,
                ozet_istatistikler: stats,
                haftalik_istihbarat_bulteni: narratives,
                hedef_ve_kesfedilen_yazarlar: authors,
                incelenen_entryler: entries
            };
            const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `troll_radar_istihbarat_bulteni_${currentDays}d.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else if (format === 'csv') {
            let csvContent = "\uFEFF";
            csvContent += "TROLLRADAR // EKŞİ SÖZLÜK İSTİHBARAT RAPORU\n";
            csvContent += `Oluşturulma Tarihi,${new Date().toISOString()}\n`;
            csvContent += `Analiz Periyodu (Gün),${currentDays}\n`;
            csvContent += `Toplam Entry,${stats.total_entries_period || entries.length}\n`;
            csvContent += `Koordineli Entry,${stats.coordinated_entries_period || 0}\n\n`;

            csvContent += "--- BÖLÜM 1: HAFTALIK İSTİHBARAT BÜLTENİ & MANİPÜLASYON ODAKLARI ---\n";
            csvContent += "Kategori,Başlık,Koordineli Entry,Aktif Yazarlar,Özet Değerlendirme\n";
            narratives.forEach(n => {
                csvContent += `"${(n.category || '').replace(/"/g, '""')}","${(n.title || '').replace(/"/g, '""')}",${n.coordinated_count || 0},"${(n.authors || []).join(', ')}","${(n.summary || '').replace(/"/g, '""')}"\n`;
            });
            csvContent += "\n";

            csvContent += "--- BÖLÜM 2: HEDEF VE TESPİT EDİLEN YAZARLAR DOSYASI ---\n";
            csvContent += "Yazar Adı,Risk Skoru,Dönem Entry,Koordineli Operasyon,Odak Konuları\n";
            authors.forEach(a => {
                csvContent += `"${a.nick}",%${a.risk_score || 0},${a.period_entries || 0},${a.coordinated_entries || 0},"${(a.top_topics || []).join(', ')}"\n`;
            });
            csvContent += "\n";

            csvContent += "--- BÖLÜM 3: İNCELENEN ENTRY LİSTESİ ---\n";
            csvContent += "ID,Yazar,Başlık,Kategori,Tarih,Favori,Koordineli,Metin\n";
            entries.forEach(e => {
                csvContent += `${e.id},"${(e.author || '').replace(/"/g, '""')}","${(e.topic || '').replace(/"/g, '""')}","${(e.category || '').replace(/"/g, '""')}",${e.created_at},${e.favorite_count || 0},${e.is_coordinated ? 'Evet' : 'Hayır'},"${(e.content || '').replace(/\n/g, ' ').replace(/"/g, '""')}"\n`;
            });

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `troll_radar_istihbarat_raporu_${currentDays}d.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch (err) {
        console.error("Export build error:", err);
    }
}

// Global Click Listener to Close Dropdown When Clicking Outside
document.addEventListener('click', (e) => {
    const exportContainer = document.getElementById('export-container');
    if (exportContainer && !exportContainer.contains(e.target)) {
        closeExportMenu();
    }
});

// Global Keyboard Listener for Closing Modals and Menus with Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAuthorModal();
        closeScrapeModal();
        closeExportMenu();
    }
});

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
