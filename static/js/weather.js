(async function () {
  function el(selector) { return document.querySelector(selector); }
  function els(selector) { return Array.from(document.querySelectorAll(selector)); }

  const locationTextEls = {
    desktop: el('#desktop-location-text'),
    mobile: el('#mobile-location-text'),
  };

  let PH_CITIES = {};
  async function loadPHCities() {
      try {
          const res = await fetch("/api/cities");
          PH_CITIES = await res.json();
          console.log("Loaded PH city list:", Object.keys(PH_CITIES).length);
      } catch (e) {
          console.error("Failed to load PH cities", e);
      }
  }
  loadPHCities();

  const searchInput = document.getElementById("location-search-input");
  const autocompleteBox = document.getElementById("location-autocomplete");
  const locationText = document.getElementById("desktop-location-text");

  function renderSuggestions(query) {
      const normalized = query.toLowerCase();
      autocompleteBox.innerHTML = "";

      if (!normalized) {
          autocompleteBox.style.display = "none";
          return;
      }

      const matches = Object.keys(PH_CITIES).filter(city =>
          city.toLowerCase().includes(normalized)
      );

      if (matches.length === 0) {
          autocompleteBox.style.display = "none";
          return;
      }

      autocompleteBox.style.display = "block";

      matches.forEach(city => {
          const fullDisplay = PH_CITIES[city]; // "City, Philippines"
          const div = document.createElement("div");
          div.className = "location-option";
          div.textContent = fullDisplay;

          div.onclick = () => {
              updateLocation(fullDisplay);
              locationText.textContent = fullDisplay;
              autocompleteBox.style.display = "none";
              searchInput.value = "";
          };

          autocompleteBox.appendChild(div);
      });
  }

  if (searchInput) {
      searchInput.addEventListener("input", () => {
          renderSuggestions(searchInput.value);
      });
  }

  document.addEventListener("click", (e) => {
      if (!autocompleteBox.contains(e.target) && e.target !== searchInput) {
          autocompleteBox.style.display = "none";
      }
  });

  function getSelectedCity() {
    return (locationTextEls.desktop && locationTextEls.desktop.innerText.trim()) ||
           (locationTextEls.mobile && locationTextEls.mobile.innerText.trim()) ||
           'Manila, Philippines';
  }

  async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn('Weather fetch failed', await res.text());
      return null;
    }
    return res.json();
  }

  // Update current weather card
  async function loadWeather(cityOrQuery) {
    // prefer to pass city (backend will geocode)
    const data = await fetchJSON(`/weather?city=${encodeURIComponent(cityOrQuery)}`);
    if (!data) return;

    const tempBig = document.querySelector('.temp-big');
    if (tempBig) tempBig.innerText = (typeof data.temp === 'number') ? `${data.temp}°` : '--';

    const condition = document.querySelector('.weather-card-main .fw-medium');
    if (condition) condition.innerText = data.condition || 'Unavailable';

    const locText = document.getElementById('weather-location-text');
    if (locText) locText.innerText = data.display_city || data.city || cityOrQuery;

    const details = document.querySelector('.weather-details');
    if (details) {
      details.innerHTML = `<span><i class="bi bi-wind me-1"></i> ${data.wind || '--'} km/h</span>
                           <span><i class="bi bi-droplet-fill me-1"></i> ${data.humidity || '--'}%</span>`;
    }

    // icon (Open-Meteo SVG icons)
    const iconBox = document.getElementById('weather-icon-box');
    if (iconBox && data.icon) {
        iconBox.innerHTML = `<i class="bi ${data.icon}" style="font-size: 3.5rem;"></i>`;
    }



    // provider/time display (optional small UI update if you add element)
    const providerEl = document.getElementById('weather-provider');
    if (providerEl) providerEl.innerText = data.provider || '';
    const fetchedEl = document.getElementById('weather-fetched-at');
    if (fetchedEl) fetchedEl.innerText = data.fetched_at ? `Updated: ${data.fetched_at}` : '';
  }

  // Update forecast list (Open-Meteo daily format from backend)
  async function loadForecast(cityOrQuery) {
    const data = await fetchJSON(`/forecast?city=${encodeURIComponent(cityOrQuery)}`);
    if (!data || !data.daily) return;

    const list = document.querySelector('.forecast-list');
    if (!list) return;

    // clear existing items
    list.innerHTML = '';

    data.daily.forEach((day) => {
      const d = new Date(day.date + 'T00:00:00'); // ensure parsing
      const weekday = d.toLocaleDateString(undefined, { weekday: 'long' });

      const temp = (typeof day.temp === 'number') ? `${day.temp}°` : '--';
      const min = (typeof day.min === 'number') ? `${day.min}°` : '--';

      const item = document.createElement('div');
      item.className = 'forecast-item';
      item.innerHTML = `
          <div class="d-flex align-items-center">
            <i class="bi ${day.icon} me-3 fs-5"></i>
            <span class="fw-medium">${weekday}</span>
          </div>
          <div>
            <span class="fw-bold">${day.temp}°</span>
            <span class="text-muted small">${day.min}°</span>
          </div>
      `;


      list.appendChild(item);
    });
  }

  // Hook up update when user picks a location from the UI
  window.updateLocation = function (city) {
    if (locationTextEls.desktop) locationTextEls.desktop.innerText = city;
    if (locationTextEls.mobile) locationTextEls.mobile.innerText = city;
    // persist display label
    try { localStorage.setItem('dab_city_display', city); } catch (e) {}
    loadWeather(city);
    loadForecast(city);
    const dd = document.getElementById('desktop-location-dropdown');
    if (dd) dd.style.display = 'none';
    const md = document.getElementById('mobile-location-dropdown');
    if (md) md.style.display = 'none';
  };


  // load using current selection on page load (prefer saved display if present)
  document.addEventListener('DOMContentLoaded', () => {
    const savedDisplay = localStorage.getItem('dab_city_display');
    const city = savedDisplay || getSelectedCity();
    if (locationTextEls.desktop) locationTextEls.desktop.innerText = city;
    if (locationTextEls.mobile) locationTextEls.mobile.innerText = city;
    loadWeather(city);
    loadForecast(city);
  });

})();
