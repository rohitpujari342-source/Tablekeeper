/**
 * NOCTURNE — LUXURY RESERVATION EXPERIENCE LOGIC
 * High-reliability, animated, production-grade reservation engine
 */

// 50 Verified, Category-Matched, Guaranteed-Unique Restaurant Images
const RESTAURANT_IMAGES = {
  // Mumbai (India)
  'r_mumbai_royal': '/assets/mumbai.jpg',
  'r_mumbai_bastian': 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80',
  'r_mumbai_trident': 'https://images.unsplash.com/photo-1578474846511-04ba529f0b88?auto=format&fit=crop&w=800&q=80',
  'r_mumbai_canteen': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80',
  'r_mumbai_zuma': 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80',

  // Paris (France)
  'r_lumiere': '/assets/lumiere.jpg',
  'r_maison': 'https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=800&q=80',
  'r_paris_jules': 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80',
  'r_paris_meurice': 'https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80',
  'r_paris_laperouse': 'https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=800&q=80',

  // Tokyo (Japan)
  'r_omakase': 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=800&q=80',
  'r_tokyo_roppongi': 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80',
  'r_tokyo_sukiyabashi': 'https://images.unsplash.com/photo-1611143669185-af224c5e3252?auto=format&fit=crop&w=800&q=80',
  'r_tokyo_narisawa': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80',
  'r_tokyo_parkhyatt': 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80',

  // London (UK)
  'r_velvet': 'https://images.unsplash.com/photo-1572116469696-31de0f17cc34?auto=format&fit=crop&w=800&q=80',
  'r_london_wolseley': 'https://images.unsplash.com/photo-1559339352-11d035aa65de?auto=format&fit=crop&w=800&q=80',
  'r_london_mayfair': 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=800&q=80',
  'r_london_sketch': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80',
  'r_london_ritz': 'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=800&q=80',

  // New York (USA)
  'r_nocturne': '/assets/rooftop.jpg',
  'r_ny_manhatta': 'https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=800&q=80',
  'r_ny_balthazar': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=800&q=80',
  'r_ny_eleven': 'https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=800&q=80',
  'r_ny_bernardin': 'https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=800&q=80',

  // Dubai (UAE)
  'r_dubai_atmosphere': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=800&q=80',
  'r_dubai_zuma': 'https://images.unsplash.com/photo-1541544741938-0af808871cc0?auto=format&fit=crop&w=800&q=80',
  'r_dubai_ossiano': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=800&q=80',
  'r_dubai_tresind': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80',
  'r_dubai_nusr': 'https://images.unsplash.com/photo-1558030006-450675393462?auto=format&fit=crop&w=800&q=80',

  // Rome (Italy)
  'r_toscana': 'https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?auto=format&fit=crop&w=800&q=80',
  'r_rome_pergola': 'https://images.unsplash.com/photo-1528605248644-14dd04022da1?auto=format&fit=crop&w=800&q=80',
  'r_rome_aroma': 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=800&q=80',
  'r_rome_imago': 'https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?auto=format&fit=crop&w=800&q=80',
  'r_rome_roscioli': 'https://images.unsplash.com/photo-1481931098730-318b6f776db0?auto=format&fit=crop&w=800&q=80',

  // Singapore (Singapore)
  'r_opium': 'https://images.unsplash.com/photo-1470337458703-46ad1756a187?auto=format&fit=crop&w=800&q=80',
  'r_sg_mbs': 'https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=800&q=80',
  'r_sg_odette': 'https://images.unsplash.com/photo-1560624052-449f5ddf0c31?auto=format&fit=crop&w=800&q=80',
  'r_sg_jumbo': 'https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80',
  'r_sg_atlas': 'https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=80',

  // Los Angeles (USA)
  'r_celestial': 'https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?auto=format&fit=crop&w=800&q=80',
  'r_la_spago': 'https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?auto=format&fit=crop&w=800&q=80',
  'r_la_nobu': 'https://images.unsplash.com/photo-1559329007-40df8a9345d8?auto=format&fit=crop&w=800&q=80',
  'r_la_republicue': 'https://images.unsplash.com/photo-1543007630-9710e4a00a20?auto=format&fit=crop&w=800&q=80',
  'r_la_providence': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=800&q=80',

  // Berlin (Germany)
  'r_anker': '/assets/anker.jpg',
  'r_berlin_borchardt': 'https://images.unsplash.com/photo-1484659619207-9165d119dafe?auto=format&fit=crop&w=800&q=80',
  'r_berlin_grill': 'https://images.unsplash.com/photo-1549488344-1f9b8d2bd1f3?auto=format&fit=crop&w=800&q=80',
  'r_berlin_timraue': 'https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=800&q=80',
  'r_berlin_facil': 'https://images.unsplash.com/photo-1498654896293-37aacf113fd9?auto=format&fit=crop&w=800&q=80'
};

class NocturneApp {
  constructor() {
    const today = new Date();
    const nextDate = new Date(today.getTime() + 86400000 * 2);
    const defaultDateStr = this.formatDate(nextDate);

    this.state = {
      token: localStorage.getItem('nocturne_token') || 'guest-token-123456',
      user: JSON.parse(localStorage.getItem('nocturne_user') || '{"id":"u_guest","email":"guest@example.com","display_name":"Guest User"}'),
      restaurants: [],
      filteredRestaurants: [],
      selectedCity: 'ALL',
      selectedRestaurantId: null,
      selectedRestaurant: null,
      selectedDate: defaultDateStr,
      selectedPartySize: 4,
      selectedTime: '19:00',
      availabilityData: null,
      selectedSlot: null,
      selectedTableId: null,
      lastIdempotencyKey: null,
      isSubmittingBooking: false,
      isLookingUp: false
    };

    this.scrollObserver = null;
    this.init();
  }

  formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  async init() {
    this.setupDateDefault();
    this.updateAuthUI();
    this.initScrollObserver();

    // Ensure valid session token
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
      dateInput.min = this.formatDate(new Date());
    }
  }

  /* ------------------------------------------------------------------ */
  /*  INTERSECTION OBSERVER FOR SCROLL MOTION                           */
  /* ------------------------------------------------------------------ */
  initScrollObserver() {
    if ('IntersectionObserver' in window) {
      this.scrollObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

      document.querySelectorAll('.reveal-on-scroll').forEach(el => {
        this.scrollObserver.observe(el);
      });
    } else {
      document.querySelectorAll('.reveal-on-scroll').forEach(el => {
        el.classList.add('in-view');
      });
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

    // Pre-fill booking form fields if present
    const nameInput = document.getElementById('booking-guest-name');
    const emailInput = document.getElementById('booking-guest-email');
    if (nameInput && !nameInput.value && this.state.user) {
      nameInput.value = this.state.user.display_name || 'Guest User';
    }
    if (emailInput && !emailInput.value && this.state.user) {
      emailInput.value = this.state.user.email || 'guest@example.com';
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
  /*  DETERMINISTIC IMAGE & RELIABLE FALLBACK SYSTEM                    */
  /* ------------------------------------------------------------------ */
  getRestaurantImage(restaurant) {
    if (!restaurant) return '/assets/hero.jpg';
    if (RESTAURANT_IMAGES[restaurant.id]) {
      return RESTAURANT_IMAGES[restaurant.id];
    }
    if (restaurant.bg_image) {
      return restaurant.bg_image;
    }
    return this.getUniqueFallbackImage(restaurant);
  }

  getUniqueFallbackImage(r) {
    // Generate a beautiful, unique deterministic SVG data URI for this venue
    const name = r.name || 'Nocturne Venue';
    const city = r.city || 'Global';
    const category = r.category || 'Luxury Fine Dining';
    const initial = name.charAt(0);
    
    // Deterministic hue from restaurant id
    let hash = 0;
    const str = r.id || name;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 45); // subtle warm gold/amber/slate hues
    
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
        <defs>
          <linearGradient id="bg-${r.id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="hsl(${30 + hue}, 20%, 9%)" />
            <stop offset="50%" stop-color="#0e131b" />
            <stop offset="100%" stop-color="hsl(${20 + hue}, 25%, 6%)" />
          </linearGradient>
          <pattern id="grid-${r.id}" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(212, 175, 55, 0.05)" stroke-width="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#bg-${r.id})" />
        <rect width="100%" height="100%" fill="url(#grid-${r.id})" />
        <circle cx="400" cy="200" r="80" fill="rgba(212, 175, 55, 0.04)" stroke="rgba(212, 175, 55, 0.25)" stroke-width="1.5" />
        <text x="400" y="225" font-family="Georgia, serif" font-size="64" font-weight="bold" fill="#E6C687" text-anchor="middle">${initial}</text>
        <text x="400" y="320" font-family="Georgia, serif" font-size="24" font-weight="600" fill="#F5F3EE" text-anchor="middle" letter-spacing="1">${name.toUpperCase()}</text>
        <text x="400" y="350" font-family="sans-serif" font-size="13" fill="#A7ADB7" text-anchor="middle" letter-spacing="2">${category.toUpperCase()} • ${city.toUpperCase()}</text>
        <path d="M 320 380 L 480 380" stroke="rgba(212, 175, 55, 0.3)" stroke-width="1" />
      </svg>
    `;

    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg.trim())}`;
  }

  handleImageError(imgEl, restaurantId) {
    if (!imgEl) return;
    const r = this.state.restaurants.find(item => item.id === restaurantId) || { id: restaurantId, name: 'Venue' };
    imgEl.onerror = null; // Prevent loop
    imgEl.src = this.getUniqueFallbackImage(r);
    imgEl.classList.add('image-fallback-active');
  }

  /* ------------------------------------------------------------------ */
  /*  RESTAURANT DISCOVERY & MULTI-CITY SYSTEM                          */
  /* ------------------------------------------------------------------ */
  async loadRestaurants() {
    try {
      const data = await this.api('/restaurants');
      const baseVenues = data.restaurants || [];

      // Fetch Full Detail for Cards in parallel
      const detailed = await Promise.all(
        baseVenues.map(r => this.api(`/restaurants/${r.id}`).catch(() => r))
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
      console.error('Failed to load restaurants:', err);
      this.showToast('Failed to load restaurants', 'error');
      const grid = document.getElementById('restaurant-grid');
      if (grid) {
        grid.innerHTML = `
          <div class="availability-error-card" style="grid-column: 1 / -1;">
            <div class="error-card-icon">⚠</div>
            <div class="error-card-content">
              <h4 class="error-title">Unable to load culinary venues</h4>
              <p class="error-desc">Server did not respond to restaurant catalog query.</p>
            </div>
            <button class="btn btn-primary btn-sm" onclick="app.loadRestaurants()">RETRY</button>
          </div>
        `;
      }
    }
  }

  populateSelectDropdowns(venues) {
    const select = document.getElementById('search-restaurant');
    if (!select) return;

    select.innerHTML = venues.map(r => `
      <option value="${r.id}">${r.name} (${r.city || r.timezone})</option>
    `).join('');

    if (this.state.selectedRestaurantId) {
      select.value = this.state.selectedRestaurantId;
    }
  }

  filterByCity(cityName) {
    this.state.selectedCity = cityName;

    // Update City Filter Chip active state
    document.querySelectorAll('.city-chip').forEach(btn => {
      const text = btn.innerText;
      if (text.includes(cityName) || (cityName === 'ALL' && text.includes('All'))) {
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
      grid.innerHTML = '<div class="text-muted" style="padding: 3rem; grid-column: 1 / -1; text-align: center;">No venues found for this selection.</div>';
      return;
    }

    grid.innerHTML = restaurants.map((r, index) => {
      const photo = this.getRestaurantImage(r);
      const tableCount = r.tables ? r.tables.length : 6;
      const category = r.category || 'Luxury Dining & Lounge';
      const city = r.city || 'Global';
      const delayMs = (index % 6) * 45;

      return `
        <div class="restaurant-card" 
             id="card-${r.id}" 
             style="--card-delay: ${delayMs}ms;"
             onclick="app.viewAvailabilityFor('${r.id}', event)">
          <div class="card-image-wrapper">
            <img src="${photo}" 
                 alt="${r.name}" 
                 class="card-image" 
                 loading="lazy" 
                 onerror="app.handleImageError(this, '${r.id}')">
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
              <button type="button" 
                      class="btn btn-sm btn-outline-gold view-availability-btn" 
                      id="btn-avail-${r.id}"
                      onclick="app.viewAvailabilityFor('${r.id}', event)">
                <span>VIEW AVAILABILITY</span>
                <span class="btn-arrow">&rarr;</span>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Attach IntersectionObserver for scroll animations
    if (this.scrollObserver) {
      grid.querySelectorAll('.restaurant-card').forEach(card => {
        this.scrollObserver.observe(card);
      });
    } else {
      grid.querySelectorAll('.restaurant-card').forEach(card => {
        card.classList.add('in-view');
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /*  VIEW AVAILABILITY FLOW — RELIABLE & ANIMATED                      */
  /* ------------------------------------------------------------------ */
  async viewAvailabilityFor(restaurantId, event) {
    if (event) {
      event.stopPropagation();
    }

    if (!restaurantId) return;

    // Immediately show feedback on button
    const btn = document.getElementById(`btn-avail-${restaurantId}`);
    if (btn) {
      btn.classList.add('is-loading');
      btn.innerHTML = `<span class="btn-spinner"></span> CHECKING...`;
    }

    try {
      let r = this.state.restaurants.find(item => item.id === restaurantId);
      if (!r || !r.tables) {
        // Fetch fresh detail if tables missing
        r = await this.api(`/restaurants/${restaurantId}`);
      }

      this.state.selectedRestaurantId = restaurantId;
      this.state.selectedRestaurant = r;

      // Sync Top Form Controls
      const restSelect = document.getElementById('search-restaurant');
      if (restSelect) restSelect.value = restaurantId;

      const dateInput = document.getElementById('search-date');
      if (dateInput && dateInput.value) {
        this.state.selectedDate = dateInput.value;
      }

      const timeInput = document.getElementById('search-time');
      if (timeInput && timeInput.value) {
        this.state.selectedTime = timeInput.value;
      }

      const guestsSelect = document.getElementById('search-guests');
      if (guestsSelect && guestsSelect.value) {
        this.state.selectedPartySize = parseInt(guestsSelect.value, 10) || 4;
      }

      // Smooth scroll to view-availability
      this.scrollToSection('view-availability');

      // Load Availability
      await this.loadAvailability();

    } catch (err) {
      console.error('Error in viewAvailabilityFor:', err);
      this.showToast(`Could not load availability: ${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.classList.remove('is-loading');
        btn.innerHTML = `<span>VIEW AVAILABILITY</span><span class="btn-arrow">&rarr;</span>`;
      }
    }
  }

  async selectRestaurantAndSearch(restaurantId) {
    await this.viewAvailabilityFor(restaurantId);
  }

  async handleSearchSubmit(e) {
    if (e) e.preventDefault();

    const restaurantId = document.getElementById('search-restaurant')?.value;
    const date = document.getElementById('search-date')?.value;
    const guests = parseInt(document.getElementById('search-guests')?.value, 10) || 4;
    const timeEl = document.getElementById('search-time');
    const time = timeEl ? timeEl.value : '19:00';

    if (!restaurantId || !date) {
      this.showToast('Please select a restaurant and date', 'warning');
      return;
    }

    this.state.selectedRestaurantId = restaurantId;
    this.state.selectedDate = date;
    this.state.selectedPartySize = guests;
    this.state.selectedTime = time;

    const btn = document.getElementById('btn-search-tables');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'SEARCHING...';
    }

    try {
      this.state.selectedRestaurant = await this.api(`/restaurants/${restaurantId}`);
      this.scrollToSection('view-availability');
      await this.loadAvailability();
    } catch (err) {
      this.showToast(`Search failed: ${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'FIND A TABLE';
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /*  THEMED VENUE DETAIL & AVAILABILITY FLOOR PLAN                     */
  /* ------------------------------------------------------------------ */
  async loadAvailability() {
    const r = this.state.selectedRestaurant;
    if (!r) return;

    this.updateVenueThemeBanner(r);

    const dateSummary = document.getElementById('avail-summary-date');
    if (dateSummary) dateSummary.innerText = this.state.selectedDate;

    const timeSummary = document.getElementById('avail-summary-time');
    if (timeSummary) timeSummary.innerText = this.state.selectedTime;

    const guestSummary = document.getElementById('avail-summary-guests');
    if (guestSummary) guestSummary.innerText = `${this.state.selectedPartySize} Guests`;

    const errorCard = document.getElementById('availability-error-card');
    const loadingState = document.getElementById('availability-loading-state');
    const timelineStrip = document.getElementById('timeline-strip');
    const floorplanContainer = document.getElementById('floorplan-container');

    if (errorCard) errorCard.style.display = 'none';
    if (loadingState) loadingState.style.display = 'block';
    if (timelineStrip) timelineStrip.style.opacity = '0.35';
    if (floorplanContainer) floorplanContainer.style.opacity = '0.35';

    try {
      const data = await this.api(
        `/availability?restaurant_id=${r.id}&date=${this.state.selectedDate}&party_size=${this.state.selectedPartySize}`
      );

      this.state.availabilityData = data;
      this.renderTimelineStrip(data.slots || []);

    } catch (err) {
      console.error('Availability API error:', err);
      if (errorCard) {
        errorCard.style.display = 'flex';
        const msg = document.getElementById('availability-error-message');
        if (msg) msg.innerText = err.message || 'Could not load availability for the selected date.';
      }
      this.showToast(`Availability error: ${err.message}`, 'error');
    } finally {
      if (loadingState) loadingState.style.display = 'none';
      if (timelineStrip) timelineStrip.style.opacity = '1';
      if (floorplanContainer) floorplanContainer.style.opacity = '1';
    }
  }

  updateVenueThemeBanner(r) {
    const banner = document.getElementById('venue-theme-banner');
    if (banner) {
      const bg = this.getRestaurantImage(r);
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
      strip.innerHTML = '<div class="text-muted" style="padding: 1.5rem; text-align: center; width: 100%;">No available slots for this date & party size. Please choose another date or smaller party.</div>';
      this.renderFloorPlan(null);
      this.updateSummaryPanel();
      return;
    }

    // Try matching requested time
    let activeSlot = slots.find(s => s.starts_at_local.endsWith(this.state.selectedTime));
    if (!activeSlot && slots.length > 0) {
      // Pick first slot with available tables
      activeSlot = slots.find(s => s.available_table_ids && s.available_table_ids.length > 0) || slots[0];
    }

    strip.innerHTML = slots.map(s => {
      const timeStr = s.starts_at_local.split('T')[1];
      const count = s.available_table_ids ? s.available_table_ids.length : 0;
      const isSelected = activeSlot && s.starts_at_local === activeSlot.starts_at_local;
      const isDisabled = count === 0;

      return `
        <div class="timeline-slot ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}"
             role="button"
             tabindex="${isDisabled ? -1 : 0}"
             onclick="${!isDisabled ? `app.selectSlot('${s.starts_at_local}')` : ''}">
          <div class="slot-time">${timeStr}</div>
          <div class="slot-count">${count > 0 ? `${count} free` : 'full'}</div>
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

    const timeLabel = document.getElementById('selected-slot-time-label');
    if (timeLabel) timeLabel.innerText = this.state.selectedTime;

    const timeSummary = document.getElementById('avail-summary-time');
    if (timeSummary) timeSummary.innerText = this.state.selectedTime;

    // Highlight timeline slot in DOM
    document.querySelectorAll('.timeline-slot').forEach(el => {
      const slotTimeEl = el.querySelector('.slot-time');
      if (slotTimeEl && slotTimeEl.innerText === this.state.selectedTime) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });

    // Auto-select first AVAILABLE table
    const freeTables = slot.available_table_ids || [];
    if (freeTables.length > 0) {
      if (!freeTables.includes(this.state.selectedTableId)) {
        this.state.selectedTableId = freeTables[0];
      }
    } else {
      this.state.selectedTableId = null;
    }

    this.renderFloorPlan(slot);
    this.updateSummaryPanel();
  }

  renderFloorPlan(slot) {
    const grid = document.getElementById('tables-grid');
    if (!grid || !this.state.selectedRestaurant) return;

    const tables = this.state.selectedRestaurant.tables || [];
    const freeTableIds = new Set((slot && slot.available_table_ids) || []);

    if (tables.length === 0) {
      grid.innerHTML = '<div class="text-muted" style="padding: 2rem;">No table specifications configured.</div>';
      return;
    }

    grid.innerHTML = tables.map(t => {
      const isAvailable = freeTableIds.has(t.id);
      const isSelected = isAvailable && t.id === this.state.selectedTableId;
      const statusText = isSelected ? '✓ SELECTED' : (isAvailable ? 'AVAILABLE' : 'RESERVED');
      const seats = Array.from({ length: Math.min(t.capacity, 8) }).map(() => '<span class="seat-dot"></span>').join('');

      return `
        <div class="table-card ${isSelected ? 'selected' : ''} ${!isAvailable ? 'unavailable' : ''}"
             role="button"
             tabindex="${isAvailable ? 0 : -1}"
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
        const txt = document.getElementById('combined-tables-text');
        if (txt) {
          txt.innerText = `Tables 1 & 2 can be seamlessly joined to accommodate up to ${this.state.selectedPartySize} guests.`;
        }
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
    const tableLabel = tableObj ? `Table ${tableObj.label} (Capacity: ${tableObj.capacity})` : (tableId ? `Table ${tableId}` : 'None Available');

    const restEl = document.getElementById('summary-restaurant');
    if (restEl) restEl.innerText = r.name;

    const dtEl = document.getElementById('summary-datetime');
    if (dtEl) dtEl.innerText = `${this.state.selectedDate} at ${this.state.selectedTime}`;

    const partyEl = document.getElementById('summary-party');
    if (partyEl) partyEl.innerText = `${this.state.selectedPartySize} Guests`;

    const tableEl = document.getElementById('summary-table');
    if (tableEl) tableEl.innerText = tableLabel;

    const confirmBtn = document.getElementById('btn-confirm-booking');
    if (confirmBtn) {
      if (!tableId) {
        confirmBtn.disabled = true;
        confirmBtn.innerText = 'NO AVAILABLE TABLE SELECTED';
      } else {
        confirmBtn.disabled = false;
        confirmBtn.innerText = 'CONFIRM RESERVATION';
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /*  CONFIRMATION & BOOKING SUBMISSION WITH IDEMPOTENCY                */
  /* ------------------------------------------------------------------ */
  async handleConfirmReservation() {
    if (this.state.isSubmittingBooking) return; // Prevent double submit

    if (!this.state.selectedRestaurant || !this.state.selectedTableId) {
      this.showToast('Please select an available table to confirm', 'warning');
      return;
    }

    const guestNameInput = document.getElementById('booking-guest-name');
    const guestEmailInput = document.getElementById('booking-guest-email');
    const guestName = (guestNameInput && guestNameInput.value.trim()) || (this.state.user && this.state.user.display_name) || 'Guest User';
    const guestEmail = (guestEmailInput && guestEmailInput.value.trim()) || (this.state.user && this.state.user.email) || 'guest@example.com';

    this.state.isSubmittingBooking = true;
    const btn = document.getElementById('btn-confirm-booking');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="btn-spinner"></span> SECURING TABLE...`;
    }

    // Generate unique Idempotency Key (UUID style)
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
      this.renderConfirmationModal(res, guestName);
      this.openConfirmationModal();
      this.showToast('Reservation confirmed & saved to backend!', 'success');

      // Refresh My Reservations list
      await this.fetchUserReservations();

    } catch (err) {
      console.error('Booking failed:', err);

      if (err.status === 409 || err.status === 422 || err.code === 'conflict' || err.code === 'table_unavailable') {
        this.showToast('Table is no longer available. Refreshing floor plan...', 'error');
        await this.loadAvailability();
      } else {
        this.showToast(`Booking error: ${err.message}`, 'error');
      }
    } finally {
      this.state.isSubmittingBooking = false;
      if (btn) {
        btn.disabled = !this.state.selectedTableId;
        btn.innerText = 'CONFIRM RESERVATION';
      }
    }
  }

  renderConfirmationModal(res, guestName) {
    const refEl = document.getElementById('confirmation-ref');
    if (refEl) refEl.innerText = res.reference || 'REF-CONFIRMED';

    const restEl = document.getElementById('conf-restaurant');
    if (restEl) restEl.innerText = this.state.selectedRestaurant.name;

    const dtEl = document.getElementById('conf-datetime');
    if (dtEl) dtEl.innerText = `${res.starts_at_local || res.starts_at}`;

    const partyEl = document.getElementById('conf-party');
    if (partyEl) partyEl.innerText = `${res.party_size} Guests`;
    
    const tableObj = (this.state.selectedRestaurant.tables || []).find(t => t.id === res.table_id);
    const tableEl = document.getElementById('conf-table');
    if (tableEl) tableEl.innerText = tableObj ? `Table ${tableObj.label}` : res.table_id;

    const guestEl = document.getElementById('conf-guest-name');
    if (guestEl) guestEl.innerText = guestName || (this.state.user?.display_name || 'Guest User');
  }

  openConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    if (modal) modal.classList.add('active');
  }

  closeConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    if (modal) modal.classList.remove('active');
  }

  copyReferenceCode() {
    const refCode = document.getElementById('confirmation-ref')?.innerText;
    if (refCode) {
      navigator.clipboard.writeText(refCode).then(() => {
        const btn = document.getElementById('btn-copy-ref');
        if (btn) {
          btn.innerText = 'Copied!';
          setTimeout(() => { btn.innerText = 'Copy'; }, 2000);
        }
        this.showToast(`Reference ${refCode} copied to clipboard`, 'success');
      }).catch(() => {
        this.showToast(refCode, 'info');
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /*  RESERVATION LOOKUP FEATURE                                        */
  /* ------------------------------------------------------------------ */
  async handleLookupSubmit(event) {
    if (event) event.preventDefault();
    if (this.state.isLookingUp) return;

    const input = document.getElementById('lookup-ref-input');
    const container = document.getElementById('lookup-result-container');
    const btn = document.getElementById('btn-lookup-ref');

    if (!input || !container) return;

    const reference = input.value.trim().toUpperCase();
    if (!reference) {
      this.showToast('Please enter a reservation reference', 'warning');
      return;
    }

    this.state.isLookingUp = true;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="btn-spinner"></span> LOOKING UP...`;
    }

    container.style.display = 'block';
    container.innerHTML = `
      <div class="skeleton" style="height: 80px; border-radius: var(--radius-md);"></div>
    `;

    try {
      const record = await this.api(`/reservations/${reference}`);
      const isConfirmed = record.status?.toLowerCase() === 'confirmed';
      const venue = this.state.restaurants.find(rest => rest.id === record.restaurant_id);
      const venueName = venue ? venue.name : record.restaurant_id;

      container.innerHTML = `
        <div class="reservation-card" style="border-color: var(--border-medium); background: var(--bg-surface-elevated);">
          <div>
            <span class="status-badge ${isConfirmed ? 'confirmed' : 'cancelled'}">
              ● ${record.status.toUpperCase()}
            </span>
            <div style="font-family: monospace; font-size: 0.9rem; color: var(--accent-champagne); font-weight: bold; margin-top: 0.4rem;">
              REF: ${record.reference}
            </div>
          </div>

          <div>
            <strong style="font-family: var(--font-serif); font-size: 1.35rem;">${venueName}</strong>
            <div style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.2rem;">
              📅 ${record.starts_at_local || record.starts_at} &nbsp;|&nbsp; 👥 ${record.party_size} Guests &nbsp;|&nbsp; 🪑 Table ${record.table_id}
            </div>
          </div>

          <div>
            <span class="text-muted" style="font-size: 0.8rem;">Verified in Backend</span>
          </div>

          <div>
            ${isConfirmed ? `
              <button class="btn btn-secondary btn-sm" onclick="app.cancelReservation('${record.reference}')">
                Cancel
              </button>
            ` : `
              <span class="text-muted" style="font-size: 0.85rem;">Cancelled</span>
            `}
          </div>
        </div>
      `;
      this.showToast(`Found reservation ${reference}`, 'success');
    } catch (err) {
      container.innerHTML = `
        <div class="availability-error-card">
          <div class="error-card-icon">✕</div>
          <div class="error-card-content">
            <h4 class="error-title">Reservation Not Found</h4>
            <p class="error-desc">No active record found for reference <strong>${reference}</strong> under the current user account.</p>
          </div>
        </div>
      `;
    } finally {
      this.state.isLookingUp = false;
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'LOOKUP';
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /*  MY RESERVATIONS LIST & CANCELLATIONS                              */
  /* ------------------------------------------------------------------ */
  async fetchUserReservations() {
    const container = document.getElementById('my-reservations-list');
    const refreshBtn = document.getElementById('btn-refresh-reservations');
    if (!container) return;

    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.innerText = 'Refreshing...';
    }

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
        const isConfirmed = r.status && r.status.toLowerCase() === 'confirmed';
        const venue = this.state.restaurants.find(rest => rest.id === r.restaurant_id);
        const venueName = venue ? venue.name : r.restaurant_id;

        return `
          <div class="reservation-card" id="res-card-${r.reference}">
            <div>
              <span class="status-badge ${isConfirmed ? 'confirmed' : 'cancelled'}">
                ● ${r.status ? r.status.toUpperCase() : 'UNKNOWN'}
              </span>
              <div style="font-family: monospace; font-size: 0.85rem; color: var(--accent-champagne); margin-top: 0.4rem;">
                REF: ${r.reference}
              </div>
            </div>

            <div>
              <strong style="font-family: var(--font-serif); font-size: 1.3rem;">${venueName}</strong>
              <div style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.2rem;">
                📅 ${r.starts_at_local || r.starts_at} &nbsp;|&nbsp; 👥 ${r.party_size} Guests &nbsp;|&nbsp; 🪑 Table ${r.table_id}
              </div>
            </div>

            <div>
              <span class="text-muted" style="font-size: 0.8rem;">Saved in Backend</span>
            </div>

            <div>
              ${isConfirmed ? `
                <button class="btn btn-secondary btn-sm" id="cancel-btn-${r.reference}" onclick="app.cancelReservation('${r.reference}')">
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
      container.innerHTML = `<div class="text-muted" style="padding: 1.5rem;">Error loading reservations: ${err.message}</div>`;
    } finally {
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerText = 'Refresh';
      }
    }
  }

  async cancelReservation(reference) {
    if (!confirm(`Are you sure you want to cancel reservation ${reference}?`)) return;

    const cancelBtn = document.getElementById(`cancel-btn-${reference}`);
    if (cancelBtn) {
      cancelBtn.disabled = true;
      cancelBtn.innerText = 'Cancelling...';
    }

    try {
      await this.api(`/reservations/${reference}/cancel`, { method: 'POST' });
      this.showToast(`Reservation ${reference} cancelled successfully`, 'success');
      await this.fetchUserReservations();
    } catch (err) {
      this.showToast(`Cancellation error: ${err.message}`, 'error');
      if (cancelBtn) {
        cancelBtn.disabled = false;
        cancelBtn.innerText = 'Cancel';
      }
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
      <span style="font-weight: bold; color: var(--accent-champagne); font-size: 1.1rem;">${icon}</span>
      <span style="font-size: 0.9rem; color: var(--text-primary); line-height: 1.4;">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 350);
    }, 4500);
  }
}

// Global App Instance
window.app = new NocturneApp();
