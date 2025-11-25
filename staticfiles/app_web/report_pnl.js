// AJAX-enhanced P&L filter: submit form via fetch and replace the table and period labels without full-page reload
document.addEventListener('DOMContentLoaded', function(){
  // init flatpickr if available
  if (window.flatpickr){
    flatpickr('#pnl-start', {dateFormat: 'Y-m-d'});
    flatpickr('#pnl-end', {dateFormat: 'Y-m-d'});
  }

  const form = document.getElementById('pnl-filter-form');
  if (!form) return;
  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    const start = document.getElementById('pnl-start').value;
    const end = document.getElementById('pnl-end').value;

    // Build URL preserving other query params except start/end
    const url = new URL(window.location.href);
    url.searchParams.set('start', start);
    url.searchParams.set('end', end);

    // Fetch new HTML fragment (full page) and replace the card content and period labels
    fetch(url.toString(), {headers: { 'X-Requested-With': 'XMLHttpRequest' }})
      .then(r => r.text())
      .then(html => {
        // Parse response and extract the table and period labels
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newCard = doc.getElementById('pnl-card');
        const newPeriods = doc.getElementById('pnl-periods');
        if (newCard) {
          document.getElementById('pnl-card').innerHTML = newCard.innerHTML;
        }
        if (newPeriods) {
          document.getElementById('pnl-periods').innerHTML = newPeriods.innerHTML;
        }
        // update browser URL without reload
        window.history.replaceState({}, '', url);
      })
      .catch(err => console.error('Failed to refresh P&L:', err));
  });

  // print button
  const printBtn = document.getElementById('printBtn');
  if (printBtn){
    printBtn.addEventListener('click', function(){
      window.print();
    });
  }
});

