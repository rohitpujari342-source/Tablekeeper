/**
 * NOCTURNE — MULTI-CITY & THEMED VENUE APPLICATION LOGIC
 */

class NocturneApp {
  constructor() {
    this.state = {
      token: localStorage.getItem('nocturne_token') || 'guest-token-123456',
      user: JSON.parse(localStorage.getItem('nocturne_user') || '{"id":"u_guest","email":"guest@example.com","display_name":"Guest User"}'),
      restaurants: [],
      filteredRestaurants: [],
      selectedCity: 'ALL',
      selectedRestaurant: null,
      selectedDate: new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0], // 2 days in future
      selectedPartySize: 4,
      selectedTime: '19:00',
      availabilityData: null,
      selectedSlot: null,
      selectedTableId: null,
      lastIdempotencyKey: null,
    };

    this.init();
  }

  async init() {
    this.setupDateDefault();
    this.updateAuthUI();

    // Guarantee valid guest session token
    if (!this.state.token) {
      this.state.token = 'guest-token-123456';
      this.state.user = { id: 'u_guest', email: 'guest@example.com', display_name: 'Guest User' };
      localStorage.setItem('nocturne_token', this.state.token);
      localStorage.setItem('nocturne_user', JSON.stringify(this.state.user));
    }

    await this.loadRestaurants();
    await this.fetchUserReservations();
  }

  setupDateDefault() {
    const dateInput = document.getElementById('search-date');
    if (dateInput) {
      dateInput.value = this.state.selectedDate;
      dateInput.min = new Date().toISOString().split('T')[0];
    }
  }

  /* ------------------------------------------------------------------ */
  /*  API HTTP CLIENT                                                   */
  /* ------------------------------------------------------------------ */
  async api(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers || {})
    };

    if (this.state.token) {
      headers['Authorization'] = `Bearer ${this.state.token}`;
    }

    try {
      const response = await fetch(path, { ...options, headers });
      
      let data = null;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      }

      if (!response.ok) {
        const error = new Error((data && data.error && data.error.message) || `HTTP ${response.status}`);
        error.status = response.status;
        error.code = data && data.error ? data.error.code : 'error';
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      console.error(`API Error [${path}]:`, err);
      throw err;
    }
  }

  /* ------------------------------------------------------------------ */
  /*  CONTINUOUS SCROLL NAVIGATION                                      */
  /* ------------------------------------------------------------------ */
  scrollToSection(sectionId) {
    const target = document.getElementById(sectionId);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
    }

    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    const navLink = document.getElementById(`nav-${sectionId.replace('view-', '')}`);
    if (navLink) navLink.classList.add('active');
  }

  /* ------------------------------------------------------------------ */
  /*  AUTH SYSTEM                                                       */
  /* ------------------------------------------------------------------ */
  updateAuthUI() {
    const badge = document.getElementById('user-display-name');
    const authBtn = document.getElementById('auth-btn');

    if (this.state.user) {
      if (badge) badge.innerText = `${this.state.user.display_name || this.state.user.email}`;
      if (authBtn) {
        authBtn.innerText = 'Switch User';
        authBtn.onclick = () => this.openAuthModal();
      }
    } else {
      if (badge) badge.innerText = 'Guest User';
      if (authBtn) {
        authBtn.innerText = 'Sign In';
        authBtn.onclick = () => this.openAuthModal();
      }
    }
  }

  openAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.classList.add('active');
  }

  closeAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.classList.remove('active');
  }

  async loginAs(email, password, silent = false) {
    try {
      const data = await this.api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });

      this.state.token = data.token;
      this.state.user = data.user;
      localStorage.setItem('nocturne_token', data.token);
      localStorage.setItem('nocturne_user', JSON.stringify(data.user));

      this.updateAuthUI();
      this.closeAuthModal();

      if (!silent) {
        this.showToast(`Signed in as ${data.user.display_name || data.user.email}`, 'success');
      }

      await this.fetchUserReservations();
    } catch (err) {
      if (!silent) {
        this.showToast(err.message || 'Authentication failed', 'error');
      }
    }
  }

  async handleAuthSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    await this.loginAs(email, password);
  }

  /* ------------------------------------------------------------------ */
  /*  RESTAURANT DISCOVERY & MULTI-CITY SYSTEM                          */
  /* ------------------------------------------------------------------ */
  async loadRestaurants() {
    try {
      const data = await this.api('/restaurants');
      this.state.restaurants = data.restaurants || [];

      // Fetch Full Detail for Cards
      const detailed = await Promise.all(
        this.state.restaurants.map(r => this.api(`/restaurants/${r.id}`).catch(() => r))
      );

      this.state.restaurants = detailed;
      this.state.filteredRestaurants = detailed;

      this.populateSelectDropdowns(detailed);
      this.renderRestaurantGrid(detailed);

      // Auto load Mumbai or first restaurant
      const firstVenue = detailed.find(r => r.city === 'Mumbai') || detailed[0];
      if (firstVenue) {
        this.state.selectedRestaurantId = firstVenue.id;
        this.state.selectedRestaurant = firstVenue;
        await this.loadAvailability();
      }
    } catch (err) {
      this.showToast('Failed to load restaurants', 'error');
    }
  }

  populateSelectDropdowns(venues) {
    const select = document.getElementById('search-restaurant');
    if (!select) return;

    select.innerHTML = venues.map(r => `
      <option value="${r.id}">${r.name} (${r.city || r.timezone})</option>
    `).join('');
  }

  filterByCity(cityName) {
    this.state.selectedCity = cityName;

    // Update City Filter Chip active state
    document.querySelectorAll('.city-chip').forEach(btn => {
      if (btn.innerText.includes(cityName) || (cityName === 'ALL' && btn.innerText.includes('All'))) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    const citySelect = document.getElementById('search-city');
    if (citySelect) citySelect.value = cityName;

    const filtered = cityName === 'ALL' 
      ? this.state.restaurants 
      : this.state.restaurants.filter(r => r.city === cityName);

    this.state.filteredRestaurants = filtered;
    this.populateSelectDropdowns(filtered);
    this.renderRestaurantGrid(filtered);
  }

  handleCityFilterChange(cityName) {
    this.filterByCity(cityName);
  }

  renderRestaurantGrid(restaurants) {
    const grid = document.getElementById('restaurant-grid');
    if (!grid) return;

    if (!restaurants || restaurants.length === 0) {
      grid.innerHTML = '<div class="text-muted" style="padding: 2rem; grid-column: span 3;">No venues found in this city.</div>';
      return;
    }

    grid.innerHTML = restaurants.map(r => {
      const photo = r.bg_image || '/assets/hero.jpg';
      const tableCount = r.tables ? r.tables.length : 6;
      const category = r.category || 'Luxury Dining & Lounge';
      const city = r.city || 'Global';

      return `
        <div class="restaurant-card" onclick="app.selectRestaurantAndSearch('${r.id}')">
          <div class="card-image-wrapper">
            <img src="${photo}" alt="${r.name}" class="card-image" loading="lazy">
            <span class="card-badge">${category}</span>
            <span class="card-city-tag">📍 ${city}</span>
          </div>
          <div class="card-content">
            <h3 class="card-title">${r.name}</h3>
            <div class="card-meta">
              <span>Timezone: ${r.timezone}</span>
              <span>•</span>
              <span>🪑 ${tableCount} Tables</span>
            </div>
            
            <div class="time-slots-preview">
              <span class="slot-chip">18:00</span>
              <span class="slot-chip">18:30</span>
              <span class="slot-chip">19:00</span>
              <span class="slot-chip">19:30</span>
              <span class="slot-chip">20:00</span>
            </div>

            <div class="card-footer">
              <span class="view-availability-link">
                VIEW AVAILABILITY &rarr;
              </span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async selectRestaurantAndSearch(restaurantId) {
    const select = document.getElementById('search-restaurant');
    if (select) select.value = restaurantId;
    await this.triggerSearch();
  }

  async handleSearchSubmit(e) {
    e.preventDefault();
    await this.triggerSearch();
  }

  async triggerSearch() {
    const restaurantId = document.getElementById('search-restaurant').value;
    const date = document.getElementById('search-date').value;
    const guests = parseInt(document.getElementById('search-guests').value, 10);
    const time = document.getElementById('search-time').value || '19:00';

    if (!restaurantId || !date) {
      this.showToast('Please select a restaurant and date', 'warning');
      return;
    }

    this.state.selectedRestaurantId = restaurantId;
    this.state.selectedDate = date;
    this.state.selectedPartySize = guests;
    this.state.selectedTime = time;

    // Fetch Restaurant Detail for table definitions
    this.state.selectedRestaurant = await this.api(`/restaurants/${restaurantId}`);

    await this.loadAvailability();
    this.scrollToSection('view-availability');
  }

  /* ------------------------------------------------------------------ */
  /*  THEMED VENUE DETAIL & AVAILABILITY FLOOR PLAN                     */
  /* ------------------------------------------------------------------ */
  async loadAvailability() {
    const r = this.state.selectedRestaurant;
    if (!r) return;

    this.updateVenueThemeBanner(r);

    document.getElementById('avail-summary-date').innerText = this.state.selectedDate;
    document.getElementById('avail-summary-guests').innerText = `${this.state.selectedPartySize} Guests`;

    try {
      const data = await this.api(
        `/availability?restaurant_id=${r.id}&date=${this.state.selectedDate}&party_size=${this.state.selectedPartySize}`
      );

      this.state.availabilityData = data;
      this.renderTimelineStrip(data.slots || []);
    } catch (err) {
      this.showToast(`Availability error: ${err.message}`, 'error');
    }
  }

  updateVenueThemeBanner(r) {
    const banner = document.getElementById('venue-theme-banner');
    if (banner) {
      const bg = r.bg_image || '/assets/hero.jpg';
      banner.style.backgroundImage = `url('${bg}')`;
    }

    const catBadge = document.getElementById('avail-venue-category');
    if (catBadge) catBadge.innerText = r.category || 'Luxury Venue';

    const nameEl = document.getElementById('avail-restaurant-name');
    if (nameEl) nameEl.innerText = r.name;

    const cityEl = document.getElementById('avail-venue-city');
    if (cityEl) cityEl.innerText = `📍 ${r.city || 'Global'}`;

    const tzEl = document.getElementById('avail-timezone');
    if (tzEl) tzEl.innerText = `Timezone: ${r.timezone}`;
  }

  renderTimelineStrip(slots) {
    const strip = document.getElementById('timeline-strip');
    if (!strip) return;

    if (!slots || slots.length === 0) {
      strip.innerHTML = '<div class="text-muted" style="padding: 1rem;">No available slots on this date.</div>';
      this.renderFloorPlan(null);
      return;
    }

    // Try matching requested time
    let activeSlot = slots.find(s => s.starts_at_local.endsWith(this.state.selectedTime));
    if (!activeSlot && slots.length > 0) {
      activeSlot = slots[0];
    }

    strip.innerHTML = slots.map(s => {
      const timeStr = s.starts_at_local.split('T')[1];
      const count = s.available_table_ids ? s.available_table_ids.length : 0;
      const isSelected = activeSlot && s.starts_at_local === activeSlot.starts_at_local;
      const isDisabled = count === 0;

      return `
        <div class="timeline-slot ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}"
             onclick="${!isDisabled ? `app.selectSlot('${s.starts_at_local}')` : ''}">
          <div class="slot-time">${timeStr}</div>
          <div class="slot-count">${count} free</div>
        </div>
      `;
    }).join('');

    if (activeSlot) {
      this.selectSlot(activeSlot.starts_at_local);
    }
  }

  selectSlot(startsAtLocal) {
    if (!this.state.availabilityData) return;
    const slot = this.state.availabilityData.slots.find(s => s.starts_at_local === startsAtLocal);
    if (!slot) return;

    this.state.selectedSlot = slot;
    this.state.selectedTime = startsAtLocal.split('T')[1];

    document.getElementById('selected-slot-time-label').innerText = this.state.selectedTime;

    // Highlight timeline strip
    document.querySelectorAll('.timeline-slot').forEach(el => {
      if (el.querySelector('.slot-time').innerText === this.state.selectedTime) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });

    // Auto select first available table
    const freeTables = slot.available_table_ids || [];
    this.state.selectedTableId = freeTables.length > 0 ? freeTables[0] : (this.state.selectedRestaurant.tables[0]?.id || null);

    this.renderFloorPlan(slot);
    this.updateSummaryPanel();
  }

  renderFloorPlan(slot) {
    const grid = document.getElementById('tables-grid');
    if (!grid || !this.state.selectedRestaurant) return;

    const tables = this.state.selectedRestaurant.tables || [];
    const freeTableIds = slot ? new Set(slot.available_table_ids || []) : new Set(tables.map(t => t.id));

    if (!this.state.selectedTableId && tables.length > 0) {
      this.state.selectedTableId = tables[0].id;
    }

    grid.innerHTML = tables.map(t => {
      const isAvailable = freeTableIds.has(t.id);
      const isSelected = t.id === this.state.selectedTableId;
      const statusText = isSelected ? '✓ SELECTED' : (isAvailable ? 'AVAILABLE' : 'RESERVED');
      const seats = Array.from({ length: Math.min(t.capacity, 8) }).map(() => '<span class="seat-dot"></span>').join('');

      return `
        <div class="table-card ${isSelected ? 'selected' : ''} ${!isAvailable ? 'unavailable' : ''}"
             onclick="${isAvailable ? `app.selectTable('${t.id}')` : ''}">
          <div class="table-header">
            <span class="table-label">Table ${t.label}</span>
            <span class="table-badge">${statusText}</span>
          </div>
          <div class="table-capacity">
            <span>Capacity: ${t.capacity} Guests</span>
            <div class="seat-dots">${seats}</div>
          </div>
        </div>
      `;
    }).join('');

    // Combined Tables Feature Display
    const combinedBanner = document.getElementById('combined-tables-banner');
    if (combinedBanner) {
      if (this.state.selectedPartySize >= 6 && tables.length >= 2) {
        combinedBanner.style.display = 'flex';
        document.getElementById('combined-tables-text').innerText = 
          `Tables 1 & 2 can be seamlessly joined to accommodate up to ${this.state.selectedPartySize} guests.`;
      } else {
        combinedBanner.style.display = 'none';
      }
    }
  }

  selectTable(tableId) {
    this.state.selectedTableId = tableId;
    if (this.state.selectedSlot) {
      this.renderFloorPlan(this.state.selectedSlot);
    } else {
      this.renderFloorPlan(null);
    }
    this.updateSummaryPanel();
  }

  updateSummaryPanel() {
    const r = this.state.selectedRestaurant;
    const tableId = this.state.selectedTableId;

    if (!r) return;

    const tableObj = (r.tables || []).find(t => t.id === tableId);
    const tableLabel = tableObj ? `Table ${tableObj.label} (Capacity: ${tableObj.capacity})` : (tableId || 'Table 1');

    document.getElementById('summary-restaurant').innerText = r.name;
    document.getElementById('summary-datetime').innerText = `${this.state.selectedDate} at ${this.state.selectedTime}`;
    document.getElementById('summary-party').innerText = `${this.state.selectedPartySize} Guests`;
    document.getElementById('summary-table').innerText = tableLabel;

    const confirmBtn = document.getElementById('btn-confirm-booking');
    if (confirmBtn) {
      confirmBtn.disabled = !tableId;
    }
  }

  /* ------------------------------------------------------------------ */
  /*  CONFIRMATION & STALE STATE RECOVERY                               */
  /* ------------------------------------------------------------------ */
  async handleConfirmReservation() {
    if (!this.state.selectedRestaurant || !this.state.selectedTableId) {
      this.showToast('Please select a table to confirm', 'warning');
      return;
    }

    const btn = document.getElementById('btn-confirm-booking');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'SECURING TABLE...';
    }

    // Generate unique Idempotency Key (UUIDv4)
    const idempotencyKey = `idempotent-key-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    this.state.lastIdempotencyKey = idempotencyKey;

    const payload = {
      restaurant_id: this.state.selectedRestaurant.id,
      table_id: this.state.selectedTableId,
      starts_at_local: `${this.state.selectedDate}T${this.state.selectedTime}`,
      party_size: this.state.selectedPartySize
    };

    try {
      const res = await this.api('/reservations', {
        method: 'POST',
        headers: {
          'Idempotency-Key': idempotencyKey
        },
        body: JSON.stringify(payload)
      });

      // Render & Show Confirmation Modal Overlay
      this.renderConfirmationModal(res);
      this.openConfirmationModal();
      this.showToast('Reservation confirmed & saved to backend!', 'success');

      // Refresh My Reservations list
      await this.fetchUserReservations();

    } catch (err) {
      console.error('Booking failed:', err);

      if (err.status === 409 || err.status === 422 || err.code === 'conflict' || err.code === 'table_unavailable') {
        // STALE STATE RECOVERY SPEC REQUIREMENT
        this.showToast('TABLE NO LONGER AVAILABLE. That table was just taken. We have refreshed availability for you.', 'error');
        await this.loadAvailability();
      } else {
        this.showToast(`Booking error: ${err.message}`, 'error');
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'CONFIRM RESERVATION';
      }
    }
  }

  renderConfirmationModal(res) {
    document.getElementById('confirmation-ref').innerText = res.reference || 'REF-CONFIRMED';
    document.getElementById('conf-restaurant').innerText = this.state.selectedRestaurant.name;
    document.getElementById('conf-datetime').innerText = `${res.starts_at_local || res.starts_at}`;
    document.getElementById('conf-party').innerText = `${res.party_size} Guests`;
    
    const tableObj = (this.state.selectedRestaurant.tables || []).find(t => t.id === res.table_id);
    document.getElementById('conf-table').innerText = tableObj ? `Table ${tableObj.label}` : res.table_id;
  }

  openConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    if (modal) modal.classList.add('active');
  }

  closeConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    if (modal) modal.classList.remove('active');
  }

  /* ------------------------------------------------------------------ */
  /*  MY RESERVATIONS                                                   */
  /* ------------------------------------------------------------------ */
  async fetchUserReservations() {
    const container = document.getElementById('my-reservations-list');
    if (!container) return;

    try {
      const data = await this.api('/reservations');
      const reservations = data.reservations || [];

      if (reservations.length === 0) {
        container.innerHTML = `
          <div class="bg-surface" style="padding: 2.5rem; text-align: center; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
            <p class="text-muted" style="margin-bottom: 1rem;">No active reservations found for this session.</p>
            <button class="btn btn-primary" onclick="app.scrollToSection('view-discover')">Explore & Book</button>
          </div>
        `;
        return;
      }

      container.innerHTML = reservations.map(r => {
        const isConfirmed = r.status === 'CONFIRMED';

        return `
          <div class="reservation-card">
            <div>
              <span class="status-badge ${isConfirmed ? 'confirmed' : 'cancelled'}">
                ● ${r.status}
              </span>
              <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-muted); margin-top: 0.4rem;">
                REF: ${r.reference}
              </div>
            </div>

            <div>
              <strong style="font-family: var(--font-serif); font-size: 1.3rem;">Venue: ${r.restaurant_id}</strong>
              <div style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.2rem;">
                📅 ${r.starts_at_local || r.starts_at} &nbsp;|&nbsp; 👥 ${r.party_size} Guests &nbsp;|&nbsp; 🪑 Table ${r.table_id}
              </div>
            </div>

            <div>
              <span class="text-muted" style="font-size: 0.8rem;">Saved in Backend</span>
            </div>

            <div>
              ${isConfirmed ? `
                <button class="btn btn-secondary btn-sm" onclick="app.cancelReservation('${r.reference}')">
                  Cancel
                </button>
              ` : `
                <span class="text-muted" style="font-size: 0.85rem;">Cancelled</span>
              `}
            </div>
          </div>
        `;
      }).join('');

    } catch (err) {
      container.innerHTML = `<div class="text-muted">Error loading reservations: ${err.message}</div>`;
    }
  }

  async cancelReservation(reference) {
    if (!confirm(`Are you sure you want to cancel reservation ${reference}?`)) return;

    try {
      await this.api(`/reservations/${reference}/cancel`, { method: 'POST' });
      this.showToast(`Reservation ${reference} cancelled successfully`, 'success');
      await this.fetchUserReservations();
    } catch (err) {
      this.showToast(`Cancellation error: ${err.message}`, 'error');
    }
  }

  /* ------------------------------------------------------------------ */
  /*  TOAST NOTIFICATIONS                                               */
  /* ------------------------------------------------------------------ */
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ');

    toast.innerHTML = `
      <span style="font-weight: bold; color: var(--accent-champagne);">${icon}</span>
      <span style="font-size: 0.9rem; color: var(--text-primary);">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }
}

// Global App Instance
window.app = new NocturneApp();
