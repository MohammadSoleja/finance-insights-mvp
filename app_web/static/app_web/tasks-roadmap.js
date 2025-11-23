// Roadmap/Timeline View - Timeline Rendering and Navigation

(function() {
  'use strict';

  let currentZoom = 'week'; // day, week, month
  let currentDate = new Date();

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', function() {
    if (window.currentView === 'roadmap') {
      initializeRoadmap();
    }
  });

  function initializeRoadmap() {
    renderTimeline();
    positionTaskBars();
    positionTodayMarker();
  }

  window.zoomTimeline = function(zoom) {
    currentZoom = zoom;

    // Update active button
    document.querySelectorAll('.zoom-controls .btn').forEach(btn => {
      btn.classList.remove('active');
    });
    event.target.classList.add('active');

    renderTimeline();
    positionTaskBars();
  };

  window.navigateTimeline = function(direction) {
    if (direction === 'today') {
      currentDate = new Date();
    } else if (direction === 'prev') {
      if (currentZoom === 'day') {
        currentDate.setDate(currentDate.getDate() - 7);
      } else if (currentZoom === 'week') {
        currentDate.setDate(currentDate.getDate() - 28);
      } else {
        currentDate.setMonth(currentDate.getMonth() - 3);
      }
    } else if (direction === 'next') {
      if (currentZoom === 'day') {
        currentDate.setDate(currentDate.getDate() + 7);
      } else if (currentZoom === 'week') {
        currentDate.setDate(currentDate.getDate() + 28);
      } else {
        currentDate.setMonth(currentDate.getMonth() + 3);
      }
    }

    renderTimeline();
    positionTaskBars();
    positionTodayMarker();
  };

  function renderTimeline() {
    const header = document.getElementById('timeline-header');
    if (!header) return;

    const { start, end, days } = getTimelineRange();

    header.innerHTML = '';

    for (let i = 0; i < days; i++) {
      const date = new Date(start);
      date.setDate(date.getDate() + i);

      const dayDiv = document.createElement('div');
      dayDiv.className = 'timeline-day';

      const isToday = isDateToday(date);
      if (isToday) {
        dayDiv.classList.add('today');
      }

      if (currentZoom === 'day') {
        dayDiv.textContent = formatDate(date, 'MMM DD');
      } else if (currentZoom === 'week') {
        if (date.getDay() === 1) { // Monday
          dayDiv.textContent = `Week ${getWeekNumber(date)}`;
        }
      } else {
        if (date.getDate() === 1) {
          dayDiv.textContent = formatDate(date, 'MMM YYYY');
        }
      }

      header.appendChild(dayDiv);
    }

    // Update current period display
    const periodDisplay = document.getElementById('current-period');
    if (periodDisplay) {
      periodDisplay.textContent = formatPeriod(start, end);
    }
  }

  function getTimelineRange() {
    const start = new Date(currentDate);
    let days;

    if (currentZoom === 'day') {
      // Show 7 days
      start.setDate(start.getDate() - 3);
      days = 7;
    } else if (currentZoom === 'week') {
      // Show 4 weeks
      start.setDate(start.getDate() - start.getDay()); // Start of week
      days = 28;
    } else {
      // Show 3 months
      start.setDate(1); // Start of month
      days = 90;
    }

    const end = new Date(start);
    end.setDate(end.getDate() + days - 1);

    return { start, end, days };
  }

  function positionTaskBars() {
    const taskBars = document.querySelectorAll('.timeline-bar');
    const { start, days } = getTimelineRange();

    taskBars.forEach(bar => {
      const taskStart = new Date(bar.dataset.start);
      const taskEnd = new Date(bar.dataset.end);

      // Calculate position
      const startOffset = Math.floor((taskStart - start) / (1000 * 60 * 60 * 24));
      const duration = Math.ceil((taskEnd - taskStart) / (1000 * 60 * 60 * 24)) + 1;

      const leftPercent = (startOffset / days) * 100;
      const widthPercent = (duration / days) * 100;

      // Only show if within visible range
      if (startOffset < days && startOffset + duration > 0) {
        bar.style.left = `${Math.max(0, leftPercent)}%`;
        bar.style.width = `${Math.min(100 - leftPercent, widthPercent)}%`;
        bar.style.display = 'flex';
      } else {
        bar.style.display = 'none';
      }
    });
  }

  function positionTodayMarker() {
    const marker = document.getElementById('today-marker');
    if (!marker) return;

    const { start, days } = getTimelineRange();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const offset = Math.floor((today - start) / (1000 * 60 * 60 * 24));

    if (offset >= 0 && offset < days) {
      const leftPercent = (offset / days) * 100;
      marker.style.left = `${leftPercent}%`;
      marker.style.display = 'block';
    } else {
      marker.style.display = 'none';
    }
  }

  // ========== UTILITY FUNCTIONS ==========

  function isDateToday(date) {
    const today = new Date();
    return date.getDate() === today.getDate() &&
           date.getMonth() === today.getMonth() &&
           date.getFullYear() === today.getFullYear();
  }

  function formatDate(date, format) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    if (format === 'MMM DD') {
      return `${months[date.getMonth()]} ${date.getDate()}`;
    } else if (format === 'MMM YYYY') {
      return `${months[date.getMonth()]} ${date.getFullYear()}`;
    }

    return date.toLocaleDateString();
  }

  function formatPeriod(start, end) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
      return `${months[start.getMonth()]} ${start.getDate()}-${end.getDate()}, ${start.getFullYear()}`;
    } else if (start.getFullYear() === end.getFullYear()) {
      return `${months[start.getMonth()]} ${start.getDate()} - ${months[end.getMonth()]} ${end.getDate()}, ${start.getFullYear()}`;
    } else {
      return `${months[start.getMonth()]} ${start.getFullYear()} - ${months[end.getMonth()]} ${end.getFullYear()}`;
    }
  }

  function getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
    return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
  }

})();

