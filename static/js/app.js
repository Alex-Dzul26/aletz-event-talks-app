document.addEventListener('DOMContentLoaded', () => {
  // App State
  let rawData = null;
  let allItems = [];
  let currentCategory = 'ALL';
  let searchQuery = '';
  const selectedItems = new Map(); // id -> item object

  // DOM Elements
  const refreshBtn = document.getElementById('refreshBtn');
  const refreshSpinner = document.getElementById('refreshSpinner');
  const exportCsvBtn = document.getElementById('exportCsvBtn');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');
  const lastUpdatedText = document.getElementById('lastUpdatedText');
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const categoryFilters = document.getElementById('categoryFilters');
  const entriesList = document.getElementById('entriesList');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');

  // Floating Selection Bar
  const selectionBar = document.getElementById('selectionBar');
  const selectedCount = document.getElementById('selectedCount');
  const tweetSelectedBtn = document.getElementById('tweetSelectedBtn');
  const clearSelectionBtn = document.getElementById('clearSelectionBtn');

  // Tweet Modal
  const tweetModal = document.getElementById('tweetModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const tweetTextarea = document.getElementById('tweetTextarea');
  const charCounter = document.getElementById('charCounter');
  const copyTweetBtn = document.getElementById('copyTweetBtn');
  const launchTweetBtn = document.getElementById('launchTweetBtn');
  const toast = document.getElementById('toast');

  // Theme Management
  initTheme();

  function initTheme() {
    const savedTheme = localStorage.getItem('bq_theme') || 'dark';
    applyTheme(savedTheme, false);

    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme, true);
    });
  }

  function applyTheme(theme, notify = false) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('bq_theme', theme);
    
    if (theme === 'light') {
      themeIcon.textContent = '🌙';
      themeToggleBtn.title = 'Cambiar a Modo Oscuro';
      if (notify) showToast('Modo Claro activado ☀️');
    } else {
      themeIcon.textContent = '☀️';
      themeToggleBtn.title = 'Cambiar a Modo Claro';
      if (notify) showToast('Modo Oscuro activado 🌙');
    }
  }

  // Initial Fetch
  loadFeed(false);

  // Event Listeners
  refreshBtn.addEventListener('click', () => {
    loadFeed(true);
  });

  exportCsvBtn.addEventListener('click', exportToCsv);

  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    clearSearchBtn.style.display = searchQuery ? 'block' : 'none';
    renderFeed();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    renderFeed();
  });

  resetFiltersBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    currentCategory = 'ALL';
    updateCategoryPillActive();
    renderFeed();
  });

  categoryFilters.addEventListener('click', (e) => {
    const pill = e.target.closest('.pill');
    if (!pill) return;
    currentCategory = pill.getAttribute('data-category');
    updateCategoryPillActive();
    renderFeed();
  });

  // Modal actions
  closeModalBtn.addEventListener('click', closeTweetModal);
  tweetModal.addEventListener('click', (e) => {
    if (e.target === tweetModal) closeTweetModal();
  });

  tweetTextarea.addEventListener('input', updateCharCount);

  // Hashtag buttons
  document.querySelectorAll('.tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tag = btn.getAttribute('data-tag');
      if (!tweetTextarea.value.includes(tag)) {
        tweetTextarea.value = (tweetTextarea.value.trim() + ' ' + tag).trim();
        updateCharCount();
      }
    });
  });

  copyTweetBtn.addEventListener('click', () => {
    copyToClipboard(tweetTextarea.value, 'Tweet copied to clipboard!');
  });

  launchTweetBtn.addEventListener('click', () => {
    const text = tweetTextarea.value.trim();
    if (!text) return;
    const tweetUrl = `https://x.com/intent/tweet?text=${encodeURIComponent(text)}`;
    window.open(tweetUrl, '_blank', 'noopener,noreferrer');
  });

  // Selection Bar Actions
  clearSelectionBtn.addEventListener('click', () => {
    selectedItems.clear();
    updateSelectionUI();
    renderFeed();
  });

  tweetSelectedBtn.addEventListener('click', () => {
    if (selectedItems.size === 0) return;
    openTweetModalForSelected();
  });

  // Main Feed Loader
  async function loadFeed(forceRefresh = false) {
    setLoading(true);
    try {
      const url = `/api/feed${forceRefresh ? '?refresh=true' : ''}`;
      const response = await fetch(url);
      const resData = await response.json();

      if (!response.ok || !resData.success) {
        throw new Error(resData.error || 'Failed to fetch release notes feed.');
      }

      rawData = resData.data;
      
      // Flatten all items with parent entry reference
      allItems = [];
      rawData.entries.forEach(entry => {
        entry.items.forEach(item => {
          allItems.push({
            ...item,
            entryDate: entry.title,
            entryUpdated: entry.updated,
            entryLink: entry.link
          });
        });
      });

      updateCategoryCounts();
      updateLastUpdatedMeta();
      renderFeed();

      if (forceRefresh) {
        showToast('Feed refreshed with latest Google Cloud data.');
      }
    } catch (err) {
      console.error('Error fetching feed:', err);
      showToast(`Error: ${err.message}`, 4000);
    } finally {
      setLoading(false);
    }
  }

  function setLoading(isLoading) {
    if (isLoading) {
      refreshBtn.disabled = true;
      refreshSpinner.classList.add('spinning');
      if (!rawData) {
        loadingState.classList.remove('hidden');
        entriesList.classList.add('hidden');
      }
    } else {
      refreshBtn.disabled = false;
      refreshSpinner.classList.remove('spinning');
      loadingState.classList.add('hidden');
      entriesList.classList.remove('hidden');
    }
  }

  function updateLastUpdatedMeta() {
    if (!rawData) return;
    const updatedDate = rawData.updated ? new Date(rawData.updated).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }) : 'Recently';
    lastUpdatedText.textContent = `Feed Updated: ${updatedDate} (${rawData.total_items} items)`;
  }

  function updateCategoryCounts() {
    const counts = { ALL: allItems.length, Feature: 0, Security: 0, Changed: 0, Fixed: 0, Deprecated: 0 };
    allItems.forEach(item => {
      const cat = item.category || 'Update';
      if (counts[cat] !== undefined) {
        counts[cat]++;
      }
    });

    document.getElementById('countAll').textContent = counts.ALL;
    document.getElementById('countFeature').textContent = counts.Feature;
    document.getElementById('countSecurity').textContent = counts.Security;
    document.getElementById('countChanged').textContent = counts.Changed;
    document.getElementById('countFixed').textContent = counts.Fixed;
    document.getElementById('countDeprecated').textContent = counts.Deprecated;
  }

  function updateCategoryPillActive() {
    document.querySelectorAll('.filter-categories .pill').forEach(pill => {
      if (pill.getAttribute('data-category') === currentCategory) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
  }

  // Render Function
  function renderFeed() {
    if (!rawData) return;

    entriesList.innerHTML = '';
    let totalVisibleItems = 0;

    rawData.entries.forEach(entry => {
      // Filter items in this entry
      const matchingItems = entry.items.filter(item => {
        const matchesCat = currentCategory === 'ALL' || item.category.toLowerCase() === currentCategory.toLowerCase();
        if (!matchesCat) return false;

        if (!searchQuery) return true;
        const textToSearch = `${entry.title} ${item.category} ${item.plain_text}`.toLowerCase();
        return textToSearch.includes(searchQuery);
      });

      if (matchingItems.length === 0) return;
      totalVisibleItems += matchingItems.length;

      // Group Container
      const groupEl = document.createElement('div');
      groupEl.className = 'release-group';

      // Date Header
      const headerEl = document.createElement('div');
      headerEl.className = 'release-date-header';
      headerEl.innerHTML = `
        <h2 class="release-date-title">📅 ${escapeHtml(entry.title)}</h2>
        <a href="${escapeHtml(entry.link)}" target="_blank" rel="noopener noreferrer" class="release-date-link">
          Official Release Note ↗
        </a>
      `;
      groupEl.appendChild(headerEl);

      // Render Item Cards
      matchingItems.forEach(item => {
        const isSelected = selectedItems.has(item.id);
        const card = document.createElement('div');
        card.className = `item-card ${isSelected ? 'selected' : ''}`;
        card.id = `card-${item.id}`;

        const badgeClass = getBadgeClass(item.category);

        card.innerHTML = `
          <div class="item-top-row">
            <div class="item-left-meta">
              <input type="checkbox" class="select-checkbox" data-id="${item.id}" ${isSelected ? 'checked' : ''} />
              <span class="badge ${badgeClass}">${escapeHtml(item.category)}</span>
            </div>
            <div class="item-actions-quick">
              <button class="btn btn-sm btn-tweet tweet-single-btn" data-id="${item.id}" title="Tweet this update on X">
                <svg class="icon-x" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <span>Tweet</span>
              </button>
            </div>
          </div>
          <div class="item-body">${item.html}</div>
          <div class="item-actions">
            <button class="btn btn-sm btn-secondary copy-item-btn" data-id="${item.id}" title="Copiar esta novedad al portapapeles">
              📋 Copiar al portapapeles
            </button>
            <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-secondary">
              🔗 Documentación oficial ↗
            </a>
          </div>
        `;

        // Checkbox listener
        const checkbox = card.querySelector('.select-checkbox');
        checkbox.addEventListener('change', (e) => {
          if (e.target.checked) {
            selectedItems.set(item.id, { ...item, entryDate: entry.title });
            card.classList.add('selected');
          } else {
            selectedItems.delete(item.id);
            card.classList.remove('selected');
          }
          updateSelectionUI();
        });

        // Single Tweet button
        card.querySelector('.tweet-single-btn').addEventListener('click', () => {
          openTweetModalForItem({ ...item, entryDate: entry.title });
        });

        // Copy item snippet button
        const copyBtn = card.querySelector('.copy-item-btn');
        copyBtn.addEventListener('click', () => {
          const snippet = `[BigQuery ${item.category} - ${entry.title}]\n${item.plain_text}\n${item.link}`;
          copyToClipboard(snippet, '✓ Novedad copiada al portapapeles');
          
          // Visual feedback on button
          const originalText = copyBtn.innerHTML;
          copyBtn.innerHTML = '✓ ¡Copiado!';
          copyBtn.style.color = '#4ade80';
          setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.style.color = '';
          }, 2000);
        });

        groupEl.appendChild(card);
      });

      entriesList.appendChild(groupEl);
    });

    if (totalVisibleItems === 0) {
      emptyState.classList.remove('hidden');
    } else {
      emptyState.classList.add('hidden');
    }
  }

  function getBadgeClass(category) {
    const cat = (category || '').toLowerCase();
    if (cat.includes('feature')) return 'badge-feature';
    if (cat.includes('security')) return 'badge-security';
    if (cat.includes('change')) return 'badge-changed';
    if (cat.includes('fix')) return 'badge-fixed';
    if (cat.includes('deprecat')) return 'badge-deprecated';
    return 'badge-update';
  }

  function updateSelectionUI() {
    const count = selectedItems.size;
    selectedCount.textContent = count;
    if (count > 0) {
      selectionBar.classList.remove('hidden');
    } else {
      selectionBar.classList.add('hidden');
    }
  }

  // Compose Tweet For Single Item
  function openTweetModalForItem(item) {
    const prefix = `🚀 BigQuery ${item.category} (${item.entryDate}):\n\n`;
    const hashtags = `\n\n#BigQuery #GoogleCloud #DataEngineering`;
    const link = item.link || 'https://docs.cloud.google.com/bigquery/docs/release-notes';
    
    // Fit within 280 characters
    const reservedChars = prefix.length + 25 + hashtags.length + 5; // 25 for link
    const maxSnippetLen = Math.max(60, 280 - reservedChars);

    let snippet = item.plain_text;
    if (snippet.length > maxSnippetLen) {
      snippet = snippet.substring(0, maxSnippetLen - 3).trim() + '...';
    }

    const tweetText = `${prefix}${snippet}\n\n🔗 ${link}${hashtags}`;
    
    tweetTextarea.value = tweetText;
    updateCharCount();
    tweetModal.classList.remove('hidden');
  }

  // Compose Tweet For Multiple Selected Items
  function openTweetModalForSelected() {
    const items = Array.from(selectedItems.values());
    if (items.length === 1) {
      openTweetModalForItem(items[0]);
      return;
    }

    const prefix = `🚀 Latest BigQuery Updates (${items.length} features/fixes):\n\n`;
    const hashtags = `\n\n#BigQuery #GoogleCloud #DataEngineering`;
    const link = items[0].link || 'https://docs.cloud.google.com/bigquery/docs/release-notes';

    let bullets = '';
    items.forEach((item, idx) => {
      const summary = item.plain_text.length > 50 ? item.plain_text.substring(0, 47) + '...' : item.plain_text;
      bullets += `• [${item.category}] ${summary}\n`;
    });

    const tweetText = `${prefix}${bullets}\n🔗 ${link}${hashtags}`;
    tweetTextarea.value = tweetText;
    updateCharCount();
    tweetModal.classList.remove('hidden');
  }

  function closeTweetModal() {
    tweetModal.classList.add('hidden');
  }

  function updateCharCount() {
    const len = tweetTextarea.value.length;
    charCounter.textContent = `${len}/280`;

    if (len > 280) {
      charCounter.className = 'char-counter danger';
    } else if (len > 240) {
      charCounter.className = 'char-counter warning';
    } else {
      charCounter.className = 'char-counter';
    }
  }

  function copyToClipboard(text, successMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg);
      }).catch(() => {
        fallbackCopy(text, successMsg);
      });
    } else {
      fallbackCopy(text, successMsg);
    }
  }

  function fallbackCopy(text, successMsg) {
    const tempInput = document.createElement('textarea');
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    showToast(successMsg);
  }

  function showToast(message, duration = 3000) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.add('hidden');
    }, duration);
  }

  function exportToCsv() {
    if (!allItems || allItems.length === 0) {
      showToast('No hay datos disponibles para exportar.');
      return;
    }

    const headers = ['Fecha', 'Categoría', 'Descripción', 'Enlace Oficial'];
    const rows = [headers];

    allItems.forEach(item => {
      const date = item.entryDate || '';
      const category = item.category || 'Update';
      const text = (item.plain_text || '').replace(/\r?\n|\r/g, ' ').trim();
      const link = item.link || item.entryLink || '';
      rows.push([date, category, text, link]);
    });

    // RFC 4180 CSV generation with escaped quotes
    const csvContent = rows
      .map(row => row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(','))
      .join('\r\n');

    // UTF-8 BOM (\uFEFF) ensures special characters display correctly in Excel
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `bigquery-release-notes-${today}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast(`✓ Archivo CSV descargado con éxito (${allItems.length} registros)`);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
